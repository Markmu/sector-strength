"use client";

import React, { useState, useEffect } from 'react';
import {
  Shield,
  ShieldAlert,
  Search,
  ChevronDown,
  ChevronUp,
  Edit2,
  Trash2,
  UserPlus,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

/**
 * 用户角色
 */
type UserRole = 'user' | 'admin';

/**
 * 用户状态
 */
type UserStatus = 'active' | 'inactive' | 'banned';

/**
 * 用户数据类型
 */
interface UserData {
  id: string;
  email: string;
  username?: string;
  displayName?: string;
  role: UserRole;
  status: UserStatus;
  createdAt: string;
  lastLoginAt?: string;
}

/**
 * 角色徽章
 */
function RoleBadge({ role }: { role: UserRole }) {
  const config = {
    admin: { color: 'bg-purple-100 text-purple-700', label: '管理员', icon: Shield },
    user: { color: 'bg-gray-100 text-gray-700', label: '用户', icon: ShieldAlert },
  };

  const { color, label, icon: Icon } = config[role];

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${color}`}>
      <Icon className="w-3.5 h-3.5" />
      {label}
    </span>
  );
}

/**
 * 状态徽章
 */
function StatusBadge({ status }: { status: UserStatus }) {
  const config = {
    active: { color: 'bg-green-100 text-green-700', label: '活跃' },
    inactive: { color: 'bg-gray-100 text-gray-700', label: '未激活' },
    banned: { color: 'bg-red-100 text-red-700', label: '已禁用' },
  };

  const { color, label } = config[status];

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${color}`}>
      {label}
    </span>
  );
}

/**
 * 用户行组件
 */
interface UserRowProps {
  user: UserData;
  currentUserEmail: string | null;
  onRoleChange: (userId: string, newRole: UserRole) => Promise<void>;
  onStatusChange: (userId: string, newStatus: UserStatus) => Promise<void>;
  onEdit: (user: UserData) => void;
}

function UserRow({ user, currentUserEmail, onRoleChange, onStatusChange, onEdit }: UserRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [isCurrentUser, setIsCurrentUser] = useState(false);

  useEffect(() => {
    setIsCurrentUser(user.email === currentUserEmail);
  }, [user.email, currentUserEmail]);

  const handleRoleChange = async (newRole: UserRole) => {
    if (isCurrentUser) {
      alert('不能修改自己的角色');
      return;
    }
    if (!confirm(`确定要将 ${user.email} 的角色更改为 ${newRole === 'admin' ? '管理员' : '用户'}吗？`)) {
      return;
    }
    await onRoleChange(user.id, newRole);
  };

  const handleStatusChange = async (newStatus: UserStatus) => {
    if (isCurrentUser) {
      alert('不能修改自己的状态');
      return;
    }
    if (!confirm(`确定要将 ${user.email} 的状态更改为 ${newStatus} 吗？`)) {
      return;
    }
    await onStatusChange(user.id, newStatus);
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <div
        className="flex items-center justify-between p-4 hover:bg-gray-50 cursor-pointer transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4 flex-1 min-w-0">
          {/* 头像/首字母 */}
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-semibold">
            {(user.displayName || user.username || user.email || 'U').charAt(0).toUpperCase()}
          </div>

          {/* 用户信息 */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-gray-900 truncate">
                {user.displayName || user.username || '未设置'}
              </span>
              {isCurrentUser && (
                <span className="text-xs text-blue-600">(当前用户)</span>
              )}
            </div>
            <div className="text-sm text-gray-500 truncate">{user.email}</div>
          </div>

          {/* 角色和状态 */}
          <div className="flex items-center gap-2">
            <RoleBadge role={user.role} />
            <StatusBadge status={user.status} />
          </div>

          {/* 注册时间 */}
          <div className="hidden md:block text-sm text-gray-500">
            {new Date(user.createdAt).toLocaleDateString()}
          </div>

          {/* 展开/收起 */}
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </div>

      {/* 展开详情 */}
      {expanded && (
        <div className="border-t border-gray-200 p-4 bg-gray-50 space-y-4">
          {/* 用户详情 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-500">用户ID:</span>
              <span className="ml-2 font-mono text-xs">{user.id}</span>
            </div>
            <div>
              <span className="text-gray-500">用户名:</span>
              <span className="ml-2">{user.username || '-'}</span>
            </div>
            <div>
              <span className="text-gray-500">显示名:</span>
              <span className="ml-2">{user.displayName || '-'}</span>
            </div>
            <div>
              <span className="text-gray-500">最后登录:</span>
              <span className="ml-2">
                {user.lastLoginAt ? new Date(user.lastLoginAt).toLocaleString() : '从未'}
              </span>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex flex-wrap gap-3">
            {/* 角色切换 */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">角色:</span>
              <div className="flex rounded-lg border border-gray-300 overflow-hidden">
                <button
                  onClick={() => handleRoleChange('user')}
                  disabled={isCurrentUser}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    user.role === 'user'
                      ? 'bg-gray-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  } ${isCurrentUser ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  用户
                </button>
                <button
                  onClick={() => handleRoleChange('admin')}
                  disabled={isCurrentUser}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    user.role === 'admin'
                      ? 'bg-purple-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  } ${isCurrentUser ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  管理员
                </button>
              </div>
            </div>

            {/* 状态切换 */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">状态:</span>
              <div className="flex rounded-lg border border-gray-300 overflow-hidden">
                <button
                  onClick={() => handleStatusChange('active')}
                  disabled={isCurrentUser}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    user.status === 'active'
                      ? 'bg-green-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  } ${isCurrentUser ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  活跃
                </button>
                <button
                  onClick={() => handleStatusChange('inactive')}
                  disabled={isCurrentUser}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    user.status === 'inactive'
                      ? 'bg-gray-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  } ${isCurrentUser ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  未激活
                </button>
                <button
                  onClick={() => handleStatusChange('banned')}
                  disabled={isCurrentUser}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    user.status === 'banned'
                      ? 'bg-red-600 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-50'
                  } ${isCurrentUser ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  禁用
                </button>
              </div>
            </div>

            {/* 编辑按钮 */}
            <button
              onClick={() => onEdit(user)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            >
              <Edit2 className="w-4 h-4" />
              编辑详情
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * 用户编辑对话框
 */
interface EditUserDialogProps {
  user: UserData | null;
  open: boolean;
  onClose: () => void;
  onSave: (userId: string, data: Partial<UserData>) => Promise<void>;
}

function EditUserDialog({ user, open, onClose, onSave }: EditUserDialogProps) {
  const [displayName, setDisplayName] = useState('');
  const [username, setUsername] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setDisplayName(user.displayName || '');
      setUsername(user.username || '');
    }
  }, [user]);

  if (!open || !user) return null;

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await onSave(user.id, { displayName, username });
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <h3 className="text-lg font-semibold mb-4">编辑用户</h3>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              显示名
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div className="p-3 bg-gray-50 rounded-lg text-sm">
            <div className="text-gray-600">
              <div>邮箱: {user.email}</div>
              <div>角色: {user.role}</div>
              <div>状态: {user.status}</div>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {saving ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                保存
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * 用户管理主面板
 */
export default function UserManagementPanel() {
  const { accessToken } = useAuth();
  const [users, setUsers] = useState<UserData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingUser, setEditingUser] = useState<UserData | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);

  // 获取当前用户邮箱（用于禁止修改自己）
  const [currentUserEmail, setCurrentUserEmail] = useState<string | null>(null);

  useEffect(() => {
    // 从localStorage获取当前用户信息
    const userEmail = localStorage.getItem('userEmail');
    setCurrentUserEmail(userEmail);
  }, []);

  // 获取用户列表（使用模拟数据，后端API尚未实现）
  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      // TODO: 后端用户管理API尚未实现，使用模拟数据
      // const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/users`, {
      //   headers: {
      //     'Authorization': `Bearer ${accessToken}`,
      //   },
      // });
      //
      // if (!response.ok) {
      //   throw new Error('获取用户列表失败');
      // }
      //
      // const data = await response.json();
      // setUsers(data.data || []);

      // 模拟数据 - 后端API实现后应移除
      await new Promise((resolve) => setTimeout(resolve, 500));
      const mockUsers: UserData[] = [
        {
          id: '1',
          email: 'admin@test.com',
          displayName: '系统管理员',
          role: 'admin',
          status: 'active',
          createdAt: new Date().toISOString(),
          lastLoginAt: new Date().toISOString(),
        },
        {
          id: '2',
          email: 'user@test.com',
          displayName: '测试用户',
          role: 'user',
          status: 'active',
          createdAt: new Date(Date.now() - 86400000).toISOString(),
          lastLoginAt: new Date(Date.now() - 3600000).toISOString(),
        },
      ];
      setUsers(mockUsers);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [accessToken]);

  // 更改用户角色（使用模拟行为，后端API尚未实现）
  const handleRoleChange = async (userId: string, newRole: UserRole) => {
    try {
      // TODO: 后端用户管理API尚未实现，使用模拟行为
      // const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/users/${userId}/role`, {
      //   method: 'PATCH',
      //   headers: {
      //     'Authorization': `Bearer ${accessToken}`,
      //     'Content-Type': 'application/json',
      //   },
      //   body: JSON.stringify({ role: newRole }),
      // });

      // 模拟行为 - 后端API实现后应移除
      await new Promise((resolve) => setTimeout(resolve, 300));
      alert('提示: 用户管理API尚未实现，这是模拟操作。');
      await fetchUsers();
    } catch (err) {
      alert(`操作失败: ${(err as Error).message}`);
    }
  };

  // 更改用户状态（使用模拟行为，后端API尚未实现）
  const handleStatusChange = async (userId: string, newStatus: UserStatus) => {
    try {
      // TODO: 后端用户管理API尚未实现，使用模拟行为
      // const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/users/${userId}/status`, {
      //   method: 'PATCH',
      //   headers: {
      //     'Authorization': `Bearer ${accessToken}`,
      //     'Content-Type': 'application/json',
      //   },
      //   body: JSON.stringify({ status: newStatus }),
      // });

      // 模拟行为 - 后端API实现后应移除
      await new Promise((resolve) => setTimeout(resolve, 300));
      alert('提示: 用户管理API尚未实现，这是模拟操作。');
      await fetchUsers();
    } catch (err) {
      alert(`操作失败: ${(err as Error).message}`);
    }
  };

  // 编辑用户（使用模拟行为，后端API尚未实现）
  const handleEditUser = async (userId: string, data: Partial<UserData>) => {
    try {
      // TODO: 后端用户管理API尚未实现，使用模拟行为
      // const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/users/${userId}`, {
      //   method: 'PATCH',
      //   headers: {
      //     'Authorization': `Bearer ${accessToken}`,
      //     'Content-Type': 'application/json',
      //   },
      //   body: JSON.stringify(data),
      // });

      // 模拟行为 - 后端API实现后应移除
      await new Promise((resolve) => setTimeout(resolve, 300));
      alert('提示: 用户管理API尚未实现，这是模拟操作。');
      await fetchUsers();
    } catch (err) {
      throw err;
    }
  };

  // 过滤用户
  const filteredUsers = users.filter((user) => {
    const query = searchQuery.toLowerCase();
    return (
      user.email.toLowerCase().includes(query) ||
      (user.displayName && user.displayName.toLowerCase().includes(query)) ||
      (user.username && user.username.toLowerCase().includes(query))
    );
  });

  // 统计
  const stats = {
    total: users.length,
    admins: users.filter((u) => u.role === 'admin').length,
    active: users.filter((u) => u.status === 'active').length,
    banned: users.filter((u) => u.status === 'banned').length,
  };

  return (
    <div className="space-y-6">
      {/* 功能未实现提示 */}
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <AlertCircle className="h-5 w-5 text-yellow-400" />
          </div>
          <div className="ml-3">
            <p className="text-sm text-yellow-700">
              <strong>提示：</strong> 用户管理API后端尚未实现，当前显示为模拟数据。
              相关操作（角色变更、状态修改等）仅为演示效果。
            </p>
          </div>
        </div>
      </div>

      {/* 标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">用户管理</h2>
          <p className="text-gray-600 mt-1">管理用户账户、角色和权限</p>
        </div>
        <button
          onClick={fetchUsers}
          className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          刷新
        </button>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
            <div className="ml-3">
              <h4 className="text-sm font-medium text-red-800">加载失败</h4>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-gray-100 text-gray-700 rounded-lg p-4">
          <div className="text-2xl font-bold">{stats.total}</div>
          <div className="text-sm opacity-80">全部用户</div>
        </div>
        <div className="bg-purple-100 text-purple-700 rounded-lg p-4">
          <div className="text-2xl font-bold">{stats.admins}</div>
          <div className="text-sm opacity-80">管理员</div>
        </div>
        <div className="bg-green-100 text-green-700 rounded-lg p-4">
          <div className="text-2xl font-bold">{stats.active}</div>
          <div className="text-sm opacity-80">活跃</div>
        </div>
        <div className="bg-red-100 text-red-700 rounded-lg p-4">
          <div className="text-2xl font-bold">{stats.banned}</div>
          <div className="text-sm opacity-80">已禁用</div>
        </div>
      </div>

      {/* 搜索栏 */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="搜索用户（邮箱、用户名、显示名）..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
      </div>

      {/* 用户列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">加载中...</span>
        </div>
      ) : filteredUsers.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">
            {searchQuery ? '未找到匹配的用户' : '暂无用户'}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredUsers.map((user) => (
            <UserRow
              key={user.id}
              user={user}
              currentUserEmail={currentUserEmail}
              onRoleChange={handleRoleChange}
              onStatusChange={handleStatusChange}
              onEdit={(user) => {
                setEditingUser(user);
                setEditDialogOpen(true);
              }}
            />
          ))}
        </div>
      )}

      {/* 编辑对话框 */}
      <EditUserDialog
        user={editingUser}
        open={editDialogOpen}
        onClose={() => {
          setEditDialogOpen(false);
          setEditingUser(null);
        }}
        onSave={handleEditUser}
      />
    </div>
  );
}
