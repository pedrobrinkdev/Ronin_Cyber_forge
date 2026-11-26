// Confirmação de exclusão em qualquer formulário com data-confirmar
document.addEventListener('submit', function (e) {
  var msg = e.target.getAttribute('data-confirmar');
  if (msg && !window.confirm(msg)) { e.preventDefault(); }
});

// Avisos: fecham no X e somem sozinhos (erros ficam mais tempo)
document.querySelectorAll('.msg').forEach(function (m) {
  function fechar() { m.classList.add('saindo'); setTimeout(function () { m.remove(); }, 400); }
  m.querySelector('.msg-x').addEventListener('click', fechar);
  setTimeout(fechar, m.classList.contains('error') ? 9000 : 6000);
});
