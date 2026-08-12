"use client";

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Shield,
  ShieldAlert,
  Search,
  ChevronDown,
  ChevronUp,
  Edit2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { adminApi } from '@/lib/api';

/**
 * 用户角色
 */
type UserRole = 'user' | 'admin';

/**
 * 用户状态（仅二态：active / banned，对应后端 is_active）
 */
type UserStatus = 'active' | 'banned';

/**
 * 用户数据类型（驼峰字段，匹配后端 UserListItem）
 */
interface UserData {
  id: string;
  email: string;
  username?: string;
  role: UserRole;
  isActive: boolean;
  status: UserStatus;
  createdAt: string;
  lastLoginAt?: string;
}

/**
 * 用户统计
 */
interface UserStats {
  total: number;
  byRole: { admin: number; user: number };
  byStatus: { active: number; banned: number };
}

/**
 * 角色徽章
 */
function RoleBadge({ role }: { role: UserRole }) {
  const config = {
    admin: { color: 'bg-primary-light text-primary', label: '管理员', icon: Shield },
    user: { color: 'bg-secondary text-foreground', label: '用户', icon: ShieldAlert },
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
    active: { color: 'bg-fall/10 text-fall', label: '活跃' },
    banned: { color: 'bg-rise/10 text-rise', label: '已禁用' },
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
    <div className="border border-border rounded-lg overflow-hidden">
      <div
        className="flex items-center justify-between p-4 hover:bg-secondary cursor-pointer transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4 flex-1 min-w-0">
          {/* 头像/首字母 */}
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-semibold">
            {(user.username || user.email || 'U').charAt(0).toUpperCase()}
          </div>

          {/* 用户信息 */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-foreground truncate">
                {user.username || user.email}
              </span>
              {isCurrentUser && (
                <span className="text-xs text-primary">(当前用户)</span>
              )}
            </div>
            <div className="text-sm text-muted-foreground truncate">{user.email}</div>
          </div>

          {/* 角色和状态 */}
          <div className="flex items-center gap-2">
            <RoleBadge role={user.role} />
            <StatusBadge status={user.status} />
          </div>

          {/* 注册时间 */}
          <div className="hidden md:block text-sm text-muted-foreground">
            {new Date(user.createdAt).toLocaleDateString()}
          </div>

          {/* 展开/收起 */}
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-faint" />
          ) : (
            <ChevronDown className="w-5 h-5 text-faint" />
          )}
        </div>
      </div>

      {/* 展开详情 */}
      {expanded && (
        <div className="border-t border-border p-4 bg-secondary space-y-4">
          {/* 用户详情 */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">用户ID:</span>
              <span className="ml-2 font-mono text-xs">{user.id}</span>
            </div>
            <div>
              <span className="text-muted-foreground">用户名:</span>
              <span className="ml-2">{user.username || '-'}</span>
            </div>
            <div>
              <span className="text-muted-foreground">最后登录:</span>
              <span className="ml-2">
                {user.lastLoginAt ? new Date(user.lastLoginAt).toLocaleString() : '从未'}
              </span>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex flex-wrap gap-3">
            {/* 角色切换 */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">角色:</span>
              <div className="flex rounded-lg border border-border overflow-hidden">
                <button
                  onClick={() => handleRoleChange('user')}
                  disabled={isCurrentUser}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    user.role === 'user'
                      ? 'bg-foreground text-background'
                      : 'bg-card text-foreground hover:bg-secondary'
                  } ${isCurrentUser ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  用户
                </button>
                <button
                  onClick={() => handleRoleChange('admin')}
                  disabled={isCurrentUser}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    user.role === 'admin'
                      ? 'bg-primary text-on-signal'
                      : 'bg-card text-foreground hover:bg-secondary'
                  } ${isCurrentUser ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  管理员
                </button>
              </div>
            </div>

            {/* 状态切换 */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">状态:</span>
              <div className="flex rounded-lg border border-border overflow-hidden">
                <button
                  onClick={() => handleStatusChange('active')}
                  disabled={isCurrentUser}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    user.status === 'active'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-card text-foreground hover:bg-secondary'
                  } ${isCurrentUser ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  激活
                </button>
                <button
                  onClick={() => handleStatusChange('banned')}
                  disabled={isCurrentUser}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    user.status === 'banned'
                      ? 'bg-destructive text-destructive-foreground'
                      : 'bg-card text-foreground hover:bg-secondary'
                  } ${isCurrentUser ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  禁用
                </button>
              </div>
            </div>

            {/* 编辑按钮 */}
            <button
              onClick={() => onEdit(user)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-primary hover:bg-primary-light rounded-lg transition-colors"
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
  const [username, setUsername] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user) {
      setUsername(user.username || '');
    }
  }, [user]);

  if (!open || !user) return null;

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await onSave(user.id, { username });
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-foreground/35 flex items-center justify-center z-50 p-4">
      <div className="bg-card rounded-lg shadow-xl max-w-md w-full p-6">
        <h3 className="text-lg font-semibold mb-4">编辑用户</h3>

        {error && (
          <div className="mb-4 p-3 bg-rise/10 border border-rise/30 rounded-lg text-sm text-destructive">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
            />
          </div>

          <div className="p-3 bg-secondary rounded-lg text-sm">
            <div className="text-muted-foreground">
              <div>邮箱: {user.email}</div>
              <div>角色: {user.role === 'admin' ? '管理员' : '用户'}</div>
              <div>状态: {user.status === 'active' ? '活跃' : '已禁用'}</div>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 text-foreground hover:bg-secondary rounded-lg transition-colors disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary-hover transition-colors disabled:opacity-50 flex items-center gap-2"
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

  // 列表/分页/搜索
  const [users, setUsers] = useState<UserData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [searchInput, setSearchInput] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // 统计
  const [stats, setStats] = useState<UserStats>({
    total: 0,
    byRole: { admin: 0, user: 0 },
    byStatus: { active: 0, banned: 0 },
  });

  // 编辑对话框
  const [editingUser, setEditingUser] = useState<UserData | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);

  // 当前用户邮箱（用于禁止修改自己）
  const [currentUserEmail, setCurrentUserEmail] = useState<string | null>(null);

  useEffect(() => {
    const userEmail = localStorage.getItem('userEmail');
    setCurrentUserEmail(userEmail);
  }, []);

  // 搜索 debounce：350ms 后提交查询并复位到第 1 页
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (searchDebounceRef.current) {
      clearTimeout(searchDebounceRef.current);
    }
    searchDebounceRef.current = setTimeout(() => {
      setSearchQuery(searchInput.trim());
      setPage(1);
    }, 350);
    return () => {
      if (searchDebounceRef.current) clearTimeout(searchDebounceRef.current);
    };
  }, [searchInput]);

  // 加载用户列表 + 统计
  const loadUsers = useCallback(
    async (pageToLoad: number, query: string) => {
      setLoading(true);
      setError(null);
      try {
        const [listRes, statsRes] = await Promise.all([
          adminApi.listUsers({ q: query || undefined, page: pageToLoad, pageSize }),
          adminApi.getUserStats(),
        ]);

        const mapped: UserData[] = (listRes.data?.items || []).map((u) => ({
          id: u.id,
          email: u.email,
          username: u.username ?? undefined,
          role: u.role,
          isActive: u.isActive,
          status: u.isActive ? 'active' : 'banned',
          createdAt: u.createdAt,
          lastLoginAt: u.lastLoginAt ?? undefined,
        }));

        setUsers(mapped);
        setTotal(listRes.data?.total ?? 0);
        setTotalPages(listRes.data?.totalPages ?? 0);

        if (statsRes.data) {
          setStats({
            total: statsRes.data.total,
            byRole: statsRes.data.byRole,
            byStatus: statsRes.data.byStatus,
          });
        }
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [pageSize]
  );

  // 触发加载：page / searchQuery / accessToken 变化时
  useEffect(() => {
    if (accessToken) {
      loadUsers(page, searchQuery);
    }
  }, [accessToken, page, searchQuery, loadUsers]);

  // 更改用户角色
  const handleRoleChange = async (userId: string, newRole: UserRole) => {
    try {
      await adminApi.updateUserRole(userId, newRole);
      await loadUsers(page, searchQuery);
    } catch (err) {
      alert(`角色修改失败: ${(err as Error).message}`);
    }
  };

  // 更改用户状态
  const handleStatusChange = async (userId: string, newStatus: UserStatus) => {
    try {
      await adminApi.updateUserStatus(userId, newStatus === 'active');
      await loadUsers(page, searchQuery);
    } catch (err) {
      alert(`状态修改失败: ${(err as Error).message}`);
    }
  };

  // 编辑用户（仅 username）
  const handleEditUser = async (userId: string, data: Partial<UserData>) => {
    try {
      await adminApi.updateUser(userId, { username: data.username });
      await loadUsers(page, searchQuery);
    } catch (err) {
      throw err;
    }
  };

  return (
    <div className="space-y-6">
      {/* 标题（已移除刷新按钮） */}
      <div>
        <h2 className="text-2xl font-bold text-foreground">用户管理</h2>
        <p className="text-muted-foreground mt-1">管理用户账户、角色和权限</p>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4">
          <div className="flex">
            <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0" />
            <div className="ml-3">
              <h4 className="text-sm font-medium text-destructive">加载失败</h4>
              <p className="mt-1 text-sm text-destructive">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* 统计卡片（从 /admin/users/stats 获取） */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-secondary text-foreground rounded-lg p-4">
          <div className="text-2xl font-bold">{stats.total}</div>
          <div className="text-sm opacity-80">全部用户</div>
        </div>
        <div className="bg-primary-light text-primary rounded-lg p-4">
          <div className="text-2xl font-bold">{stats.byRole.admin}</div>
          <div className="text-sm opacity-80">管理员</div>
        </div>
        <div className="bg-fall/10 text-fall rounded-lg p-4">
          <div className="text-2xl font-bold">{stats.byStatus.active}</div>
          <div className="text-sm opacity-80">活跃</div>
        </div>
        <div className="bg-rise/10 text-rise rounded-lg p-4">
          <div className="text-2xl font-bold">{stats.byStatus.banned}</div>
          <div className="text-sm opacity-80">已禁用</div>
        </div>
      </div>

      {/* 搜索栏 */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-faint" />
        <input
          type="text"
          placeholder="搜索用户（邮箱、用户名）..."
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          className="w-full pl-10 pr-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
        />
      </div>

      {/* 用户列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <span className="ml-3 text-muted-foreground">加载中...</span>
        </div>
      ) : users.length === 0 ? (
        <div className="text-center py-12 bg-card rounded-lg border border-border">
          <AlertCircle className="w-12 h-12 text-faint mx-auto mb-4" />
          <p className="text-muted-foreground">
            {searchQuery ? '未找到匹配的用户' : '暂无用户'}
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {users.map((user) => (
              <UserRow
                key={user.id}
                user={user}
                currentUserEmail={currentUserEmail}
                onRoleChange={handleRoleChange}
                onStatusChange={handleStatusChange}
                onEdit={(u) => {
                  setEditingUser(u);
                  setEditDialogOpen(true);
                }}
              />
            ))}
          </div>

          {/* 分页 */}
          <div className="flex items-center justify-between pt-2">
            <div className="text-sm text-muted-foreground">
              共 {total} 条 · 第 {page} / {totalPages} 页
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || loading}
                className="flex items-center gap-1 px-3 py-1.5 text-sm border border-border rounded-lg hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                上一页
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages || loading}
                className="flex items-center gap-1 px-3 py-1.5 text-sm border border-border rounded-lg hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                下一页
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </>
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
