import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { authApi, ApiError } from '../../lib/api';

export const LoginForm: React.FC = () => {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
    // 清除错误信息
    if (error) setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const response = await authApi.login(formData);
      login(response.token, response.user);
      navigate('/');
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || '登录失败，请检查用户名和密码');
      } else {
        setError('网络错误，请稍后重试');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-black text-gray-900 uppercase tracking-wide">
            锁芯社区
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            登录您的账户
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="neo-brutal-card bg-red-50 border-red-500 p-4">
              <p className="text-red-700 font-medium">{error}</p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-sm font-bold text-gray-700 uppercase tracking-wide">
                用户名
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                className="neo-brutal-input w-full mt-1"
                placeholder="输入用户名"
                value={formData.username}
                onChange={handleChange}
                disabled={isLoading}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-bold text-gray-700 uppercase tracking-wide">
                密码
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="neo-brutal-input w-full mt-1"
                placeholder="输入密码"
                value={formData.password}
                onChange={handleChange}
                disabled={isLoading}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="neo-brutal-button w-full py-3 px-4 bg-black text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? '登录中...' : '登录'}
            </button>
          </div>

          <div className="text-center">
            <p className="text-sm text-gray-600">
              还没有账户？{' '}
              <Link
                to="/register"
                className="font-bold text-black hover:underline"
              >
                立即注册
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
};