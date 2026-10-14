'use strict';

(() => {
  const dialog = document.getElementById('signupDialog');
  const password = document.getElementById('signupPassword');
  const confirmation = document.getElementById('signupPasswordConfirm');

  // UI only until authentication endpoints are connected; never submit credentials
  // to the map route or persist passwords in browser storage.
  document.getElementById('loginForm').addEventListener('submit', event => {
    event.preventDefault();
    document.getElementById('loginMessage').textContent = '로그인 기능은 아직 연결되지 않았습니다.';
  });
  document.getElementById('signupOpen').addEventListener('click', () => dialog.showModal());
  document.getElementById('signupClose').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    document.getElementById('signupForm').reset();
    confirmation.setCustomValidity('');
    document.getElementById('signupMessage').textContent = '';
  });
  function validateConfirmation() {
    confirmation.setCustomValidity(confirmation.value && password.value !== confirmation.value
      ? '비밀번호가 일치하지 않습니다.' : '');
  }
  password.addEventListener('input', validateConfirmation);
  confirmation.addEventListener('input', validateConfirmation);
  document.getElementById('signupForm').addEventListener('submit', event => {
    event.preventDefault();
    validateConfirmation();
    if (!event.currentTarget.reportValidity()) return;
    document.getElementById('signupMessage').textContent = '회원가입 기능은 아직 연결되지 않았습니다.';
  });
})();
