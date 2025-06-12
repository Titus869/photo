// // 等待 DOM 加载完毕
// document.addEventListener('DOMContentLoaded', function() {
//   // 选中表单
//   const loginForm = document.getElementById('loginForm');

//   // 监听表单提交
//   loginForm.addEventListener('submit', function(event) {
//     event.preventDefault(); // 阻止表单真正提交

//     // 获取输入框的值
//     const username = document.getElementById('username').value.trim();
//     const password = document.getElementById('password').value.trim();

//     // 简单判断
//     if (username === '' || password === '') {
//       passwordError.style.display = 'block';
//       passwordError.textContent = 'Please fill in all fields!';
//       return;
//     } else {
//       window.location.href = 'main.html';
//     }
//   });
// });


document.addEventListener('DOMContentLoaded', function() {
  const loginForm = document.getElementById('loginForm');
  const passwordError = document.getElementById('passwordError'); 

  loginForm.addEventListener('submit', function(event) {
    event.preventDefault(); // 阻止默认提交

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();

    if (username === '' || password === '') {
      passwordError.style.display = 'block';
      passwordError.textContent = 'Please fill in all fields!';
      return;
    } else {
      // 调用 Flask 登录接口
      fetch('http://127.0.0.1:5000/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password}),
        credentials: 'include'
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          localStorage.setItem('username', username);
          window.location.href = 'main.html';
        } else {
          passwordError.style.display = 'block';
          passwordError.textContent = data.message || 'Login failed!';
        }
      })
      .catch(error => {
        passwordError.style.display = 'block';
        passwordError.textContent = 'Network error, please try again.';
        console.error('Error:', error);
      });
    }
  });
});
