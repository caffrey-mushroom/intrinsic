// Back link for note pages opened from a weekly: ?from=track/<group>/<issue>/ (set by tools/weekly-sources)
// or a same-site referrer under /track/. Plain browser back works either way.
(function () {
  var a = document.querySelector('.backrow .back');
  if (!a) return;
  var root = new URL('../../', location.href);           // site root (notes/<slug>/ -> ../../)
  var from = new URLSearchParams(location.search).get('from') || '';
  var target = null;
  if (/^track\/[a-z0-9-]+(\/[a-z0-9-]+)*\/?$/.test(from)) {
    target = new URL(from.replace(/\/?$/, '/') + '#weekly-sources', root);
  } else if (document.referrer) {
    try {
      var r = new URL(document.referrer);
      if (r.origin === location.origin && r.pathname.indexOf(root.pathname + 'track/') === 0) target = r;
    } catch (e) {}
  }
  if (!target) return;
  a.href = target.href;
  a.textContent = '← 返回周报';
  a.setAttribute('aria-label', '返回周报');
  // prefer real history back so the weekly keeps its scroll position
  a.addEventListener('click', function (e) {
    try {
      if (document.referrer && new URL(document.referrer).pathname === target.pathname && history.length > 1) {
        e.preventDefault(); history.back();
      }
    } catch (x) {}
  });
  var list = document.createElement('a');
  list.className = 'back'; list.href = '../'; list.textContent = 'Notes 列表';
  list.style.marginLeft = '24px';
  a.parentNode.appendChild(list);
})();
