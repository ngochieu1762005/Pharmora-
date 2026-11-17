'use strict';
const menuBtn=document.getElementById('mobileMenuBtn');
if(menuBtn){menuBtn.addEventListener('click',()=>{const menu=document.getElementById('mobileNav');menu.hidden=!menu.hidden;menuBtn.setAttribute('aria-expanded',String(!menu.hidden));});document.querySelectorAll('#mobileNav a').forEach(a=>a.addEventListener('click',()=>{document.getElementById('mobileNav').hidden=true;menuBtn.setAttribute('aria-expanded','false')}));}
document.querySelectorAll('[data-toggle]').forEach(btn=>btn.addEventListener('click',()=>{const el=document.getElementById(btn.dataset.toggle);el.type=el.type==='password'?'text':'password';btn.textContent=el.type==='password'?'Hiện':'Ẩn';}));
const form=document.getElementById('authForm');
if(form){
 const errBox=document.getElementById('formError'),btn=document.getElementById('submitBtn');
 form.addEventListener('submit',async event=>{
  event.preventDefault();errBox.hidden=true;const registration=location.pathname==='/register';const fd=new FormData(form);
  const data=Object.fromEntries(fd.entries());
  if(registration){data.demo=document.getElementById('demo').checked;data.accept=document.getElementById('accept').checked;if(data.password!==data.password_confirm){errBox.textContent='Hai mật khẩu chưa trùng khớp.';errBox.hidden=false;return;}}
  btn.disabled=true;btn.firstChild.textContent=registration?'Đang tạo tài khoản… ':'Đang đăng nhập… ';
  try{
   const response=await fetch(registration?'/api/register':'/api/login',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify(data)});
   const result=await response.json().catch(()=>({}));if(!response.ok)throw new Error(result.error||'Có lỗi khi xử lý.');
   location.assign('/app');
  }catch(e){errBox.textContent=e.message;errBox.hidden=false;btn.disabled=false;btn.firstChild.textContent=registration?'Tạo workspace miễn phí ':'Đăng nhập ';}
 });
 fetch('/api/me').then(r=>r.json()).then(session=>{if(session.authenticated)location.replace('/app')}).catch(()=>{});
}
