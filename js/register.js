// 等页面加载完毕
document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('registerForm');
  const usernameInput = document.getElementById('reg-username');
  const passwordInput = document.getElementById('reg-password');
  const confirmInput = document.getElementById('reg-confirm-password');
  const passwordError = document.getElementById('passwordError'); // 提示信息

  form.addEventListener('submit', function (event) {
    event.preventDefault(); // 阻止表单默认提交

    const username = usernameInput.value.trim();
    const password = passwordInput.value;
    const confirmPassword = confirmInput.value;

    // 简单的非空判断
    if (!username || !password || !confirmPassword) {
      passwordError.style.display = 'block';
      passwordError.textContent = 'Please fill in all fields!';
      return;
    }

    // 检查密码是否一致
    if (password !== confirmPassword) {
      passwordError.style.display = 'block';
      passwordError.textContent = 'Passwords do not match!';
      return;
    }

    // 发送注册请求
    fetch('http://127.0.0.1:5000/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          alert('Registration successful! Redirecting to login page...');
          setTimeout(() => {
            window.location.href = 'index.html';
          }, 0);
        } else {
          passwordError.style.display = 'block';
          passwordError.textContent = data.message || 'Registration failed!';
        }
      })
      .catch(error => {
        console.error('Registration request failed', error);
        passwordError.style.display = 'block';
        passwordError.textContent = 'Registration request failed!';
      });
  });
});
