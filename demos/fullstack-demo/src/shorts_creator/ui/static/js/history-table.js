(function () {
  if (window.__historyTableBound) return;
  window.__historyTableBound = true;
  function toggleRow(row) {
    var spacer = row.nextElementSibling;
    var detail = spacer && spacer.nextElementSibling;
    if (spacer) spacer.classList.toggle('hidden');
    if (detail) detail.classList.toggle('hidden');
    var chevron = row.querySelector('.chevron-icon');
    if (chevron) chevron.classList.toggle('rotate-90');
    row.setAttribute('aria-expanded', row.getAttribute('aria-expanded') === 'true' ? 'false' : 'true');
  }
  document.addEventListener('click', function (e) {
    var row = e.target.closest('[data-expandable-row]');
    if (row) toggleRow(row);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    var row = e.target.closest('[data-expandable-row]');
    if (!row) return;
    e.preventDefault();
    toggleRow(row);
  });
})();