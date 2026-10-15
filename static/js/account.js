'use strict';
(() => {
  const token = document.querySelector('meta[name="csrf-token"]').content;
  async function send(url, data) {
    const response = await fetch(url, {method: 'POST', headers: {
      'Content-Type': 'application/json', 'X-CSRF-Token': token
    }, body: JSON.stringify(data)});
    return response.json();
  }
  const login = document.getElementById('loginForm');
  const signup = document.getElementById('signupForm');
  const logout = document.getElementById('logoutButton');
  if (login) {
    if (new URLSearchParams(location.search).has('registered')) document.getElementById('loginMessage').textContent = '회원가입이 완료되었습니다. 로그인해 주세요.';
    login.addEventListener('submit', async event => {
      event.preventDefault();
      const button = login.querySelector('button[type="submit"]');
      const message = document.getElementById('loginMessage');
      button.disabled = true;
      try {
        const result = await send('/api/login', Object.fromEntries(new FormData(login)));
        if (result.ok) { location.href = '/'; return; }
        message.textContent = result.error;
        if (result.signup_required) {
          const link = document.getElementById('signupOpen');
          link.href = '/signup?username=' + encodeURIComponent(login.elements.username.value);
          link.focus();
        }
      } catch { message.textContent = '서버에 연결할 수 없습니다. 다시 시도해 주세요.'; }
      finally { button.disabled = false; }
    });
  }
  if (logout) logout.addEventListener('click', async () => {
    try {
      const result = await send('/api/logout', {});
      if (result.ok) location.reload();
      else document.getElementById('loginMessage').textContent = result.error;
    } catch { document.getElementById('loginMessage').textContent = '서버에 연결할 수 없습니다.'; }
  });
  if (!signup) return;
  signup.elements.username.value = new URLSearchParams(location.search).get('username') || '';
  document.getElementById('birthDate').max = new Date().toLocaleDateString('sv-SE');
  signup.addEventListener('submit', async event => {
    event.preventDefault();
    const message = document.getElementById('signupMessage');
    const fields = new FormData(signup);
    const data = Object.fromEntries(fields);
    data.travel_styles = fields.getAll('travel_styles');
    if (data.password !== data.password_confirmation) { message.textContent = '비밀번호가 일치하지 않습니다.'; return; }
    if (!data.travel_styles.length) { message.textContent = '여행 스타일을 하나 이상 선택해 주세요.'; return; }
    const button = signup.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      const result = await send('/api/signup', data);
      if (result.ok) { location.href = '/?registered=1'; return; }
      message.textContent = result.error;
    } catch { message.textContent = '서버에 연결할 수 없습니다. 다시 시도해 주세요.'; }
    finally { button.disabled = false; }
  });
})();

(() => {
  const form=document.getElementById('profileEditForm');
  document.querySelectorAll('input[name="mbti"]').forEach(input=>input.addEventListener('input',()=>{input.value=input.value.replace(/[^A-Za-z]/g,'').slice(0,4).toUpperCase();}));
  if(!form)return;
  const open=document.getElementById('editLoginInfoButton');
  const message=document.getElementById('profileEditMessage');
  form.elements.birth_date.max=new Date().toLocaleDateString('sv-SE');
  open.setAttribute('aria-expanded','false');open.setAttribute('aria-controls','profileEditForm');
  open.addEventListener('click',()=>{form.classList.remove('hidden');open.classList.add('hidden');open.setAttribute('aria-expanded','true');form.elements.name.focus();});
  document.getElementById('profileEditCancel').addEventListener('click',()=>{form.reset();form.classList.add('hidden');open.classList.remove('hidden');open.setAttribute('aria-expanded','false');message.textContent='';open.focus();});
  form.addEventListener('submit',async event=>{
    event.preventDefault();const fields=new FormData(form),data=Object.fromEntries(fields);data.travel_styles=fields.getAll('travel_styles');
    const button=form.querySelector('[type="submit"]');button.disabled=true;
    try{
      const response=await fetch('/api/profile',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify(data)});
      const result=await response.json();if(!response.ok||!result.ok)throw new Error(result.error||'Save failed');
      location.reload();
    }catch(error){message.textContent=error.message;}finally{button.disabled=false;}
  });
})();
