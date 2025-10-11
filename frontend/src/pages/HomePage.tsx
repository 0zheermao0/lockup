import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { postsApi } from '../lib/api';
import { Post } from '../types/index';
import { formatDistanceToNow } from '../lib/utils';

export const HomePage: React.FC = () => {
  const { user, logout } = useAuth();
  const [posts, setPosts] = useState<Post[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchPosts = async () => {
      try {
        const response = await postsApi.getPosts();
        setPosts(response.results || []);
      } catch (err) {
        setError('加载动态失败');
        console.error('Error fetching posts:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPosts();
  }, []);

  const handleLikePost = async (postId: string) => {
    try {
      const response = await postsApi.likePost(postId);
      setPosts(prev => prev.map(post =>
        post.id === postId
          ? { ...post, likes_count: response.likes_count, user_has_liked: true }
          : post
      ));
    } catch (err) {
      console.error('Error liking post:', err);
    }
  };

  const handleUnlikePost = async (postId: string) => {
    try {
      const response = await postsApi.unlikePost(postId);
      setPosts(prev => prev.map(post =>
        post.id === postId
          ? { ...post, likes_count: response.likes_count, user_has_liked: false }
          : post
      ));
    } catch (err) {
      console.error('Error unliking post:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-black border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-600 font-medium">加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b-2 border-black">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-black uppercase tracking-wide">锁芯社区</h1>
            <div className="flex items-center space-x-4">
              <div className={`px-3 py-1 rounded-full text-sm font-bold level-${user?.level || 1}`}>
                等级 {user?.level || 1}
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-yellow-500">🪙</span>
                <span className="font-bold">{user?.coins || 0}</span>
              </div>
              <button
                onClick={logout}
                className="px-3 py-1 text-sm font-medium text-gray-600 hover:text-gray-900 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
              >
                退出
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="grid gap-8 md:grid-cols-3">
          {/* Sidebar */}
          <div className="md:col-span-1">
            <div className="neo-brutal-card p-6 mb-6">
              <h3 className="font-black text-lg mb-4 uppercase tracking-wide">用户信息</h3>
              <div className="space-y-3">
                <div>
                  <span className="text-sm font-medium text-gray-600">用户名</span>
                  <p className="font-bold">{user?.username}</p>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-600">活跃度</span>
                  <p className="font-bold">{user?.activity_score || 0}</p>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-600">发布动态</span>
                  <p className="font-bold">{user?.total_posts || 0}</p>
                </div>
                <div>
                  <span className="text-sm font-medium text-gray-600">获得点赞</span>
                  <p className="font-bold">{user?.total_likes_received || 0}</p>
                </div>
              </div>
            </div>

            <div className="neo-brutal-card p-6">
              <h3 className="font-black text-lg mb-4 uppercase tracking-wide">快速操作</h3>
              <div className="space-y-3">
                <button className="neo-brutal-button w-full py-2 px-4 bg-blue-500 text-white">
                  发布动态
                </button>
                <button className="neo-brutal-button w-full py-2 px-4 bg-green-500 text-white">
                  打卡任务
                </button>
                <button className="neo-brutal-button w-full py-2 px-4 bg-purple-500 text-white">
                  小游戏
                </button>
              </div>
            </div>
          </div>

          {/* Posts Feed */}
          <div className="md:col-span-2">
            <h2 className="font-black text-xl mb-6 uppercase tracking-wide">社区动态</h2>

            {error && (
              <div className="neo-brutal-card bg-red-50 border-red-500 p-4 mb-6">
                <p className="text-red-700 font-medium">{error}</p>
              </div>
            )}

            {posts.length === 0 ? (
              <div className="neo-brutal-card p-8 text-center">
                <p className="text-gray-600 font-medium">还没有动态，快来发布第一条吧！</p>
              </div>
            ) : (
              <div className="space-y-6">
                {posts.map((post) => (
                  <div key={post.id} className="neo-brutal-card p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center space-x-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold level-${post.user.level}`}>
                          {post.user.username.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-bold">{post.user.username}</p>
                          <p className="text-sm text-gray-600">
                            {formatDistanceToNow(post.created_at)}
                          </p>
                        </div>
                      </div>
                      {post.post_type === 'checkin' && (
                        <span className="px-2 py-1 bg-green-500 text-white text-xs font-bold rounded">
                          打卡
                        </span>
                      )}
                    </div>

                    <div className="mb-4">
                      <p className="text-gray-900 whitespace-pre-wrap">{post.content}</p>
                    </div>

                    {post.images && post.images.length > 0 && (
                      <div className="mb-4 grid grid-cols-2 gap-2">
                        {post.images.map((image, index) => (
                          <img
                            key={index}
                            src={image.image}
                            alt=""
                            className="w-full h-32 object-cover border-2 border-black"
                          />
                        ))}
                      </div>
                    )}

                    <div className="flex items-center justify-between pt-4 border-t-2 border-gray-200">
                      <button
                        onClick={() =>
                          post.user_has_liked
                            ? handleUnlikePost(post.id)
                            : handleLikePost(post.id)
                        }
                        className={`flex items-center space-x-2 px-3 py-1 rounded font-medium transition-colors ${
                          post.user_has_liked
                            ? 'bg-red-500 text-white'
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                      >
                        <span>{post.user_has_liked ? '❤️' : '🤍'}</span>
                        <span>{post.likes_count}</span>
                      </button>

                      <div className="flex items-center space-x-4 text-sm text-gray-600">
                        <span>💬 {post.comments_count || 0}</span>
                        {post.location && (
                          <span>📍 位置信息</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};