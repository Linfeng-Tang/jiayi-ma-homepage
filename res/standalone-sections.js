document.addEventListener('DOMContentLoaded', function () {
  var target = document.getElementById('standalone-section');
  var sourceId = location.pathname.endsWith('students.html') ? 'students' : 'honors';
  if (!target) return;
  fetch('index.html', { cache: 'no-store' })
    .then(function (r) { return r.ok ? r.text() : Promise.reject(); })
    .then(function (html) {
      var doc = new DOMParser().parseFromString(html, 'text/html');
      var section = doc.getElementById(sourceId);
      if (!section) throw new Error('Section not found');
      target.replaceWith(section);
      section.classList.add('standalone-section');
      section.querySelectorAll('details').forEach(function (item) { item.open = true; });
    })
    .catch(function () { target.querySelector('p').textContent = '内容暂时无法载入，请稍后重试。'; });
});
