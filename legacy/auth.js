// User/password authentication against Pharmora's own Python server; no LLM provider.
let csrfToken = '';
let pharmoraUser = null;

async function apiRequest(path, {method = 'GET', data} = {}) {
  const headers = {Accept: 'application/json'};
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  if (method !== 'GET' && path !== '/api/login') headers['X-CSRF-Token'] = csrfToken;
  let response;
  try {
    response = await fetch(path, {method, headers, body: data === undefined ? undefined : JSON.stringify(data), credentials: 'same-origin'});
  } catch {
    throw new Error('Không thể kết nối máy chủ. Hãy chạy python server.py serve.');
  }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(result.error || 'Yêu cầu không thành công.');
    error.status = response.status;
    throw error;
  }
  return result;
}

function loginError(message = '') {
  const box = document.getElementById('loginError');
  box.textContent = message;
  box.hidden = !message;
}

function showLogin(message = '') {
  pharmoraUser = null;
  csrfToken = '';
  document.getElementById('appShell').hidden = true;
  document.getElementById('loginScreen').hidden = false;
  document.getElementById('loginPassword').value = '';
  loginError(message);
  document.getElementById('loginUsername').focus();
}

async function applySession(session) {
  csrfToken = session.csrf;
  pharmoraUser = session.user;
  const state = await apiRequest('/api/data');
  db = state.data;
  dataVersion = state.version;
  syncBlocked = false;
  writeQueue = Promise.resolve();
  cart = [];
  page = 'overview';
  document.getElementById('sidebarUserName').textContent = pharmoraUser.display_name;
  document.getElementById('sidebarUserRole').textContent = pharmoraUser.role === 'admin' ? 'Quản trị viên' : 'Nhân viên nhà thuốc';
  const initials = pharmoraUser.display_name.trim().split(/\s+/).slice(-2).map(x => x[0].toUpperCase()).join('');
  document.querySelectorAll('.account-avatar').forEach(e => e.textContent = initials);
  document.getElementById('manageUsersBtn').hidden = pharmoraUser.role !== 'admin';
  document.getElementById('loginScreen').hidden = true;
  document.getElementById('appShell').hidden = false;
  render();
}

async function bootstrap() {
  try {
    const session = await apiRequest('/api/me');
    if (session.authenticated) return await applySession(session);
    showLogin();
  } catch (e) {
    showLogin(e.message);
  }
}

async function submitLogin(event) {
  event.preventDefault();
  const button = document.getElementById('loginSubmit');
  button.disabled = true;
  button.textContent = 'Đang đăng nhập…';
  loginError();
  try {
    await apiRequest('/api/login', {method: 'POST', data: {
      username: document.getElementById('loginUsername').value,
      password: document.getElementById('loginPassword').value
    }});
    await applySession(await apiRequest('/api/me'));
  } catch (e) {
    loginError(e.message);
  } finally {
    button.disabled = false;
    button.textContent = 'Đăng nhập vào Pharmora';
  }
}

async function doLogout() {
  try { await writeQueue; await apiRequest('/api/logout', {method: 'POST'}); }
  catch (e) { /* Clear the interface even when the server connection is interrupted. */ }
  db = {drugs: [], orders: [], checks: [], customers: []};
  showLogin();
}

function changeMyPassword() {
  modal(`<h2>Đổi mật khẩu</h2><p>Sử dụng mật khẩu riêng, tối thiểu 10 ký tự.</p>
    <form onsubmit="submitPassword(event)">
      <label>Mật khẩu hiện tại</label><input name="oldPassword" type="password" autocomplete="current-password" required>
      <label>Mật khẩu mới</label><input name="newPassword" type="password" minlength="10" maxlength="128" autocomplete="new-password" required>
      <label>Nhập lại mật khẩu mới</label><input name="confirmPassword" type="password" minlength="10" maxlength="128" autocomplete="new-password" required>
      <div class="actions"><button type="button" onclick="closeModal()">Hủy</button><button class="primary">Cập nhật</button></div>
    </form>`);
}

async function submitPassword(event) {
  event.preventDefault();
  const form = event.target;
  const get = name => form.elements.namedItem(name).value;
  if (get('newPassword') !== get('confirmPassword')) return toast('Hai mật khẩu mới chưa trùng khớp.');
  try {
    await apiRequest('/api/password', {method: 'POST', data: {oldPassword: get('oldPassword'), newPassword: get('newPassword')}});
    closeModal();
    toast('Đã đổi mật khẩu. Các phiên đăng nhập khác đã bị đăng xuất.');
  } catch (e) { toast(e.message); }
}

async function manageUsers() {
  if (pharmoraUser?.role !== 'admin') return;
  let users;
  try { users = (await apiRequest('/api/users')).users; }
  catch (e) { return toast(e.message); }
  modal(`<h2>Quản lý tài khoản</h2><p>Chỉ quản trị viên được tạo tài khoản nhân viên. Không chia sẻ mật khẩu.</p>
    <div class="tablewrap"><table><thead><tr><th>TÀI KHOẢN</th><th>HỌ TÊN</th><th>VAI TRÒ</th></tr></thead>
      <tbody>${users.map(u => `<tr><td>${esc(u.username)}</td><td>${esc(u.display_name)}</td><td>${u.role === 'admin' ? 'Quản trị' : 'Nhân viên'}</td></tr>`).join('')}</tbody></table></div>
    <h2 style="margin:23px 0 0;font-size:14px">Thêm nhân viên</h2>
    <form onsubmit="submitUser(event)">
      <label>Tên đăng nhập</label><input name="username" pattern="[A-Za-z0-9_.\\-]{3,32}" minlength="3" maxlength="32" autocomplete="off" placeholder="vd: nhanvien01" required>
      <label>Họ tên</label><input name="display_name" minlength="2" maxlength="80" required>
      <label>Mật khẩu ban đầu (ít nhất 10 ký tự)</label><input name="password" type="password" minlength="10" maxlength="128" autocomplete="new-password" required>
      <label>Vai trò</label><select name="role"><option value="staff">Nhân viên</option><option value="admin">Quản trị viên</option></select>
      <div class="actions"><button type="button" onclick="closeModal()">Đóng</button><button class="primary">Tạo tài khoản</button></div>
    </form>`);
}

async function submitUser(event) {
  event.preventDefault();
  const f = event.target;
  const get = name => f.elements.namedItem(name).value;
  try {
    await apiRequest('/api/users', {method: 'POST', data: {username: get('username'), display_name: get('display_name'), password: get('password'), role: get('role')}});
    toast('Đã tạo tài khoản thành công.');
    await manageUsers();
  } catch (e) { toast(e.message); }
}

document.getElementById('loginForm').addEventListener('submit', submitLogin);
document.getElementById('togglePassword').addEventListener('click', () => {
  const input = document.getElementById('loginPassword');
  input.type = input.type === 'password' ? 'text' : 'password';
  document.getElementById('togglePassword').textContent = input.type === 'password' ? 'Hiện' : 'Ẩn';
});
