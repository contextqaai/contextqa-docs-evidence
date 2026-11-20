"""Account-free executable documentation loop; all source/product evidence is synthetic."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from cqa_artifacts.loop import Store
from cqa_artifacts.docs_loop import package_bundle


def seed(root,complete=False):
    root=Path(root)
    if root.exists(): raise ValueError('Choose a new demo directory')
    root.mkdir(parents=True,mode=0o700)
    store=Store(root/'docs-loop.db')
    store.create(json.loads(Path(__file__).with_name('manifest.json').read_text()))
    before='# Create a project\n\n1. Open Projects.\n2. Select Create project.\n3. Enter a name and save.\n'
    after='# Create a project\n\n1. Open Workspace.\n2. Select New project.\n3. Enter a name and save.\n'
    store.article('demo','owner','guides/projects.md','Create a project',before)
    store.article('demo','owner','guides/notifications.md','Manage notifications','# Notifications\n\nOpen Settings and choose Notifications.\n')
    event=dict(id='synthetic-release-42',source='github',title='Project creation moves into Workspace',text='Synthetic release fixture: Projects is now Workspace; Create project is now New project.',changed_paths=['src/projects/sidebar.ts'],module_ids=['projects'],source_url='https://github.com/example/product/pull/42',edits=[dict(path='guides/projects.md',before=before,after=after,reason='The synthetic release fixture changes both navigation labels.')])
    item=store.ingest('demo','owner',event)['item_id']
    store.ingest('demo','owner',dict(id='synthetic-video-7',source='video',title='New notification preferences walkthrough',text='Synthetic transcript intake: clarify which roles can change notification preferences.',module_ids=['notifications']))
    store.ingest('demo','owner',dict(id='synthetic-permissions-8',source='manual',title='Document workspace role permissions',text='Coverage request: add a role permissions guide.',module_ids=['permissions']))
    store.member('demo','owner','reviewer','contributor')
    receipt={'synthetic':True,'live_contextqa_execution':False,'remote_published':False,'item_id':item}
    if complete:
        i=store.review('demo','owner',item,1,'accept',change_id='1')
        i=store.review('demo','owner',item,i['version'],'ready')
        store.approve('demo','owner',item,i['version'],True)
        bundle=store.bundle('demo','owner',item)
        (root/'reviewed-draft.zip').write_bytes(package_bundle(bundle))
        receipt['apply_result']=store.apply_local('demo','owner',item,True)
        receipt['final_article']=store.snapshot('demo','owner')['articles']['guides/projects.md']['body']
        assert receipt['final_article']==after
        receipt['duplicate_event']=store.ingest('demo','owner',event)['duplicate']
    (root/'receipt.json').write_text(json.dumps(receipt,indent=2))
    return receipt

if __name__=='__main__':
    print(json.dumps(seed(sys.argv[1], '--complete' in sys.argv),indent=2))
