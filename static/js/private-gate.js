(() => {
  const params = new URLSearchParams(window.location.search);
  const next = params.get('next') || '/thoughts/';
  const safeNext = /^\/thoughts\/(?:[a-zA-Z0-9_-]+\/)?$/.test(next) ? next : '/thoughts/';
  document.getElementById('thoughts-next').value = safeNext;
  const message = document.getElementById('gate-message');
  if (params.get('error') === 'incorrect') message.textContent = '日数不正确，再想一想吧。';
  if (params.get('error') === 'limited') message.textContent = '尝试次数过多，请等待 15 分钟后再试。';
  if (!params.has('error')) fetch('/_private/status', {credentials: 'same-origin', cache: 'no-store'})
    .then(response => { if (response.ok) window.location.replace(safeNext); })
    .catch(() => {});
})();
