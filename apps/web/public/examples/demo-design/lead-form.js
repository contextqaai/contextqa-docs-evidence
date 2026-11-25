const form = document.querySelector('form');
const skip = form.querySelector('a[href*="#run-and-review"]');
function nextChapter() {
  return (matchMedia('(max-width: 640px)').matches ? 'mobile-player.html' : 'player.html') + '#run-and-review';
}
skip.href = nextChapter();
form.addEventListener('submit', event => {
  event.preventDefault();
  location.assign(nextChapter());
});
