"""Offline Salesforce scenario preparation. No network, execution or publication."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone, timedelta
from .core import Rejected, redact


def _confirmed(value):
    return isinstance(value, dict) and value.get('status') == 'confirmed'


def _reject_secrets(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower().replace('-', '_') in {'password', 'client_secret', 'access_token', 'refresh_token', 'authorization', 'cookie', 'api_key'}:
                raise Rejected('Do not put credentials in a Salesforce context file')
            _reject_secrets(item)
    elif isinstance(value, list):
        for item in value:
            _reject_secrets(item)


def prepare(catalog, context, now=None):
    if not isinstance(catalog, dict) or not isinstance(context, dict):
        raise Rejected('Catalog and context must be objects')
    if context.get('schemaVersion') != 1 or catalog.get('schemaVersion') != 1:
        raise Rejected('Unsupported Salesforce schema version')
    for key in ['objects', 'rules', 'personas', 'integrations', 'environment']:
        if not isinstance(context.get(key), dict):
            raise Rejected(f'{key} must be an object')
    # Schema field names can legitimately be Password or Authorization. Inspect
    # their descriptors, not their API names, while guarding actual context values.
    _reject_secrets({key: value for key, value in context.items() if key != 'objects'})
    for definition in context.get('objects', {}).values():
        if not isinstance(definition, dict) or not isinstance(definition.get('fields'), dict):
            raise Rejected('Object schema requires a fields mapping')
        for descriptor in definition['fields'].values():
            if not isinstance(descriptor, dict):
                raise Rejected('Field schema must be an object, not a record value')
            _reject_secrets(descriptor)
    assets = catalog.get('assets')
    if not isinstance(assets, list) or len(assets) > 500:
        raise Rejected('Catalog must have at most 500 assets')
    if not isinstance(context.get('orgId'), str) or not context['orgId'].strip():
        raise Rejected('An explicit org identity is required')
    now = now or datetime.now(timezone.utc)
    try:
        captured = datetime.fromisoformat(context['capturedAt'].replace('Z', '+00:00'))
        fresh = captured.tzinfo is not None and now - timedelta(days=14) <= captured <= now
    except (KeyError, TypeError, ValueError):
        fresh = False
    seen = set()
    result = []
    for asset in assets:
        if not isinstance(asset, dict) or not isinstance(asset.get('id'), str) or asset['id'] in seen:
            raise Rejected('Every asset needs a unique string ID')
        seen.add(asset['id'])
        blockers, bindings = [], {}
        if not fresh:
            blockers.append('Fresh dated context required (14-day preparation policy)')
        mappings = context.get('mappings', {})
        if not isinstance(mappings, dict):
            raise Rejected('mappings must be an object')
        for obj in asset['requiredObjects']:
            mapping = mappings.get(obj)
            actual = mapping.get('target') if _confirmed(mapping) else obj
            if not isinstance(actual, str) or actual not in context['objects']:
                blockers.append(f'Object mapping/visibility unresolved: {obj}')
            bindings[obj] = actual
        for field in asset['requiredFields']:
            obj, name = field.split('.', 1)
            mapping = mappings.get(field)
            actual = mapping.get('target') if _confirmed(mapping) else f'{bindings.get(obj, obj)}.{name}'
            if not isinstance(actual, str) or '.' not in actual:
                blockers.append(f'Field mapping unresolved: {field}')
                continue
            actual_obj, actual_field = actual.split('.', 1)
            definition = context['objects'].get(actual_obj, {})
            if not isinstance(definition, dict) or actual_field not in definition.get('fields', {}):
                blockers.append(f'Field mapping/visibility unresolved: {field}')
            bindings[field] = actual
        rule = context['rules'].get(asset['ruleKey'])
        if not (_confirmed(rule) and all(rule.get(k) for k in ['value', 'owner', 'source', 'version'])):
            blockers.append(f'Owner-confirmed rule required: {asset["ruleKey"]}')
        persona = context['personas'].get(asset['personaKey'])
        if not (_confirmed(persona) and persona.get('reference')):
            blockers.append(f'Approved persona required: {asset["personaKey"]}')
        if asset.get('integrationKey'):
            integration = context['integrations'].get(asset['integrationKey'])
            if not (_confirmed(integration) and integration.get('source') and integration.get('owner')):
                blockers.append(f'Confirmed integration mapping required: {asset["integrationKey"]}')
        if asset['requiresSandbox'] and context['environment'].get('isSandbox') is not True:
            blockers.append('Sandbox identity required by this starter asset')
        result.append({'id':asset['id'], 'version':asset['version'], 'title':asset['title'], 'module':asset['module'],
            'status':'needs_context' if blockers else 'ready_for_review', 'executed':False, 'proof':'not_checked',
            'blockers':blockers, 'bindings':bindings,
            'approvedRule':rule if _confirmed(rule) else None,
            'personaReference':persona.get('reference') if _confirmed(persona) else None,
            'steps':asset['steps'], 'requiredEvidence':asset['requiredEvidence'],
            'maintenanceTriggers':asset['maintenanceTriggers']})
    return {'schemaVersion':1, 'mode':'offline_preparation', 'orgId':context['orgId'], 'preparedAt':now.isoformat(),
        'contextHash':hashlib.sha256(json.dumps(context,sort_keys=True).encode()).hexdigest(),
        'catalogHash':hashlib.sha256(json.dumps(catalog,sort_keys=True).encode()).hexdigest(),
        'executed':False, 'executionAuthorized':False, 'scenarios':result,
        'summary':{'total':len(result),'readyForReview':sum(r['status']=='ready_for_review' for r in result),'needsContext':sum(r['status']=='needs_context' for r in result)},
        'limitations':['Schema visibility does not establish business intent or complete org coverage.',
            'Ready for review does not authorize execution or establish pass.',
            'Mappings are owner-supplied, not automatically inferred or verified.']}


def draft_guide(result, workspace):
    from . import core
    core.init(workspace, 'Salesforce scenario review — not executed')
    for scenario in result['scenarios']:
        rule = scenario['approvedRule']
        body = f"Status: {scenario['status']}; proof: not checked. "
        if rule:
            body += 'Owner-confirmed requirement: ' + str(rule['value']) + '. '
        if scenario['blockers']:
            body += 'Resolve: ' + '; '.join(scenario['blockers']) + '. '
        body += ' '.join(s['action'] + ' Expected: ' + s['expected'] for s in scenario['steps'])
        core.add_step(workspace, redact(scenario['title']), redact(body))
    # No approve/export: a human must review this draft, and no run occurred.


def context_from_sx360(snapshot):
    """Import only selected schema from a hydrated SX360 snapshot; never Apex/XML."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('components'), list):
        raise Rejected('A hydrated SX360 snapshot is required')
    if not snapshot.get('orgId') or not snapshot.get('runId') or not snapshot.get('completedAt'):
        raise Rejected('Snapshot identity, run and capture time are required')
    objects = {}
    for component in snapshot['components']:
        if not isinstance(component, dict):
            raise Rejected('Invalid snapshot component')
        if component.get('stale') or component.get('type') not in {'CustomObject', 'CustomField'}:
            continue
        content = component.get('content')
        if not isinstance(content, dict):
            raise Rejected('Hydrate SX360 component blobs before preparing context')
        if component['type'] == 'CustomObject':
            objects.setdefault(component['fullName'], {'fields': {}})
        else:
            obj, field = component['fullName'].split('.', 1)
            # Purposefully omit source code, XML, record data, descriptions and all unknown keys.
            objects.setdefault(obj, {'fields': {}})['fields'][field] = {
                key: content[key] for key in ['type', 'nillable', 'createable', 'length', 'restrictedPicklist'] if key in content}
    return {'schemaVersion':1, 'orgId':snapshot['orgId'], 'capturedAt':snapshot['completedAt'],
        'sourceSnapshotId':snapshot['runId'], 'environment':{'isSandbox':None}, 'objects':objects,
        'rules':{}, 'personas':{}, 'integrations':{}, 'execution':{'approved':False},
        'coverage':{'inventoryComplete':snapshot.get('complete') is True,
            'scope':'selected schema from hydrated SX360; confirm actual org/environment identity independently',
            'businessIntent':'unknown'}}
