import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { authApi, ApiError } from '../../lib/api-commons';

export const RegisterForm: React.FC = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    password_confirm: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
    // 清除对应字段的错误信息
    if (errors[e.target.name]) {
      setErrors(prev => ({
        ...prev,
        [e.target.name]: ''
      }));
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.username.trim()) {
      newErrors.username = '用户名不能为空';
    } else if (formData.username.length < 3) {
      newErrors.username = '用户名至少需要3个字符';
    }

    if (!formData.email.trim()) {
      newErrors.email = '邮箱不能为空';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = '请输入有效的邮箱地址';
    }

    if (!formData.password) {
      newErrors.password = '密码不能为空';
    } else if (formData.password.length < 8) {
      newErrors.password = '密码至少需要8个字符';
    }

    if (formData.password !== formData.password_confirm) {
      newErrors.password_confirm = '两次输入的密码不一致';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setErrors({});

    try {
      const response = await authApi.register(formData);
      login(response.token, response.user);
      navigate('/');
    } catch (err) {
      if (err instanceof ApiError && err.data) {
        // 处理服务器返回的字段级错误
        setErrors(err.data);
      } else {
        setErrors({ general: '注册失败，请稍后重试' });
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
            创建新账户
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {errors.general && (
            <div className="neo-brutal-card bg-red-50 border-red-500 p-4">
              <p className="text-red-700 font-medium">{errors.general}</p>
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
                className={`neo-brutal-input w-full mt-1 ${errors.username ? 'border-red-500' : ''
                  }`}
                placeholder="输入用户名"
                value={formData.username}
                onChange={handleChange}
                disabled={isLoading}
              />
              {errors.username && (
                <p className="mt-1 text-sm text-red-600">{errors.username}</p>
              )}
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-bold text-gray-700 uppercase tracking-wide">
                邮箱
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                className={`neo-brutal-input w-full mt-1 ${errors.email ? 'border-red-500' : ''
                  }`}
                placeholder="输入邮箱地址"
                value={formData.email}
                onChange={handleChange}
                disabled={isLoading}
              />
              {errors.email && (
                <p className="mt-1 text-sm text-red-600">{errors.email}</p>
              )}
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
                className={`neo-brutal-input w-full mt-1 ${errors.password ? 'border-red-500' : ''
                  }`}
                placeholder="输入密码（至少8位）"
                value={formData.password}
                onChange={handleChange}
                disabled={isLoading}
              />
              {errors.password && (
                <p className="mt-1 text-sm text-red-600">{errors.password}</p>
              )}
            </div>

            <div>
              <label htmlFor="password_confirm" className="block text-sm font-bold text-gray-700 uppercase tracking-wide">
                确认密码
              </label>
              <input
                id="password_confirm"
                name="password_confirm"
                type="password"
                required
                className={`neo-brutal-input w-full mt-1 ${errors.password_confirm ? 'border-red-500' : ''
                  }`}
                placeholder="再次输入密码"
                value={formData.password_confirm}
                onChange={handleChange}
                disabled={isLoading}
              />
              {errors.password_confirm && (
                <p className="mt-1 text-sm text-red-600">{errors.password_confirm}</p>
              )}
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="neo-brutal-button w-full py-3 px-4 bg-black text-white disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? '注册中...' : '注册'}
            </button>
          </div>

          <div className="text-center">
            <p className="text-sm text-gray-600">
              已有账户？{' '}
              <Link
                to="/login"
                className="font-bold text-black hover:underline"
              >
                立即登录
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
};