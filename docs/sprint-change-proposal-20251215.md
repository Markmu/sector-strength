# Sprint变更提案

**创建日期**: 2025-12-15
**作者**: Bob (Scrum Master)
**变更范围**: Minor - 开发团队直接实施
**审批状态**: 待审批

---

## 1. 问题摘要

### 触发来源
**Story ID**: 2.5 - API认证中间件

### 核心问题
故事2.5中设计的角色权限系统过于复杂,包含4张关联表(roles, permissions, user_roles, role_permissions)。对于当前MVP项目需求,这种设计带来诸多弊端：

1. **过度工程化**: MVP阶段只需简单角色划分(admin/user),无需复杂权限系统
2. **性能开销**: 多表JOIN查询增加数据库负担
3. **开发复杂度**: 4张表的CRUD操作和关联关系维护成本高
4. **维护困难**: 权限系统需要专门的管理界面
5. **延期风险**: 增加项目复杂度和交付时间

### 发现时机
在审查故事2.5的技术规格时,发现数据库设计过度复杂,可能影响后续开发进度。

---

## 2. 影响分析

### Epic影响
**Epic 2**: 用户认证系统 (✅ 可完成)

| 方面 | 影响 | 说明 |
|------|---------|-------|
| 当前Epic完成度 | 无影响 | 已完成的2.1、2.2、2.3故事不受影响 |
| Epic 2 验收标准 | 无冲突 | AC #4仍可完成,只是实现方式更简单 |
| 后续Epic依赖 | 无影响 | Epic 4-8的API端点权限需求更简单清晰 |

**风险评估**: 降低技术复杂度和开发风险,缩短Epic 2交付时间

### Story影响

#### **需要修改的故事**
- 故事2.5: API认证中间件 (进行中)

#### **静默受益的故事**
- 故事2.4: 用户资料管理 (已简化权限模型)
- 故事3.3-4.x: 所有受保护的API端点 (权限检查更直接)

### 技术影响分析

#### **架构文档 (Architecture.md)**
- ✅ 无冲突: 架构文档未具体指定权限实现方式
- ✅ 更吻合: 简化后的方案更符合架构的"简洁高效"原则

#### **数据模型**
- ❌ 原方案: 4张新表 + 复杂关联关系
- ✅ 新方案: 修改1张现有表(users) + 2个新字段

#### **API设计**
- ✅ 无冲突: JWT认证中间件接口保持不变
- ✅ 更简单: 权限检查直接在JWT令牌中携带角色信息

#### **代码库**
**需要新建的文件**:
- `server/alembic/versions/2025_12_15_add_role_to_users.py` - 数据库迁移(新增)

**需要修改的文件**:
- `docs/stories/2.5.api-auth-middleware.md` - 更新故事描述(修改)
- `server/src/models/user.py` - 添加role字段(修改)
- `server/src/api/auth/auth.py` - 更新JWT生成逻辑(修改)

**不再需要创建的文件**:
- ❌ `server/src/models/role.py` - 不再需要
- ❌ `server/src/models/permission.py` - 不再需要
- ❌ `server/src/api/roles.py` - 不再需要

---

## 3. 推荐方案

### 选择的方案: **直接调整(Direct Adjustment)**

#### **方案说明**
修改故事2.5的技术规格,简化数据库设计,直接在users表存储角色信息。

#### **理由**
1. **实施方便**: 仅需修改1个数据表,开发工作量小
2. **性能优越**: 权限检查无需多表JOIN,单表查询即可
3. **足够MVP**: 满足当前项目需求(admin/user角色划分)
4. **易于扩展**: 将来如需更复杂权限系统,可在此基础扩展
5. **风险低**: 架构层不增加新技术或组件

#### **努力估算**
- **开发时间**: 2-3小时(相比原方案8-12小时)
- **测试时间**: 1-2小时(相比原方案4-6小时)
- **部署复杂度**: 极低 - 单次数据库迁移

#### **时间线影响**
- **Story 2.5开发时间**: 从3-4天缩短至1天
- **Epic 2完成时间**: 无影响,甚至可能提前
- **整体项目风险**: 降低技术复杂度,减少延期可能

#### **风险评估**
- **技术风险**: ✅ 极低 - 使用当前技术栈即可实现
- **性能风险**: ✅ 极低 - 性能反而提升
- **回滚风险**: ✅ 低 - 变更仅涉及数据模型,易回滚

---

## 4. 详细变更提案

### **4.1 故事2.5 - API认证中间件**

#### **4.1.1 数据库设计更新**

❌ **原内容**(L114-L148):
```sql
-- 角色表
CREATE TABLE roles (id SERIAL PRIMARY KEY, name VARCHAR(50) UNIQUE NOT NULL, ...)
-- 权限表
CREATE TABLE permissions (id SERIAL PRIMARY KEY, name VARCHAR(100) UNIQUE NOT NULL, ...)
-- 用户角色关联表
CREATE TABLE user_roles (user_id INTEGER REFERENCES users(id), role_id INTEGER REFERENCES roles(id), ...)
-- 角色权限关联表
CREATE TABLE role_permissions (role_id INTEGER REFERENCES roles(id), permission_id INTEGER REFERENCES permissions(id), ...)
```

✅ **新内容**:
```python
# 在 server/src/models/user.py 中添加
role = Column(String(20), default='user', nullable=False, index=True, comment="用户角色: admin, user")
permissions = Column(JSON, default=list, comment="用户权限列表(JSON)")
```

#### **4.1.2 任务清单更新**

❌ **原内容**(L39-51):
```markdown
### 访问控制实现
- [ ] 定义角色和权限系统
  - [ ] 创建角色模型（Role）
  - [ ] 创建权限模型（Permission）
  - [ ] 创建用户角色关联表
  - [ ] 创建角色权限关联表
- [ ] 实现权限检查逻辑
  - [ ] 基于角色的端点保护
  - [ ] 基于资源的所有权验证
  - [ ] 支持权限继承
- [ ] 创建默认角色和权限
  ...
```

✅ **新内容**:
```markdown
### 访问控制实现(简化版)
- [ ] 在users表添加角色字段
  - [ ] 添加role列(VARCHAR enum: 'admin'/'user')
  - [ ] 添加permissions列(JSONB数组)
  - [ ] 创建数据库迁移脚本
- [ ] 实现基于角色的访问控制
  - [ ] 更新JWT令牌包含用户角色
  - [ ] 实现require_role装饰器
  - [ ] 实现require_permission装饰器
- [ ] 创建默认用户角色
  - [ ] 注册时自动分配'user'角色
  - [ ] 管理员用户特殊处理(在数据库中手动设置)
```

#### **4.1.3 技术需求更新**

❌ **原内容**(L79-82):
```markdown
- JWT验证：PyJWT or FastAPI JWT Auth
- 缓存：Redis for rate limiting
- 数据库：新增权限相关表
- 异步支持：FastAPI async中间件
```

✅ **新内容**:
```markdown
- JWT验证：PyJWT or FastAPI JWT Auth
- 缓存：Redis for rate limiting
- 数据库：修改users表结构(添加2个字段)
- 异步支持：FastAPI async中间件
```

#### **4.1.4 依赖更新**

❌ **原内容**(L204):
```markdown
- 故事2.2完成（JWT实现）
- Redis配置（用于速率限制）
- 数据库迁移脚本（4个表）
```

✅ **新内容**:
```markdown
- 故事2.2完成（JWT实现）
- Redis配置（用于速率限制）
- 数据库迁移脚本（users表添加字段）
```

### **4.2 数据库迁移脚本**

**文件**: `server/alembic/versions/2025_12_15_add_role_to_users.py`

```python
"""在users表添加角色和权限字段

Revision ID: xxxxxxxx
Revises: 2025_12_13_1635-6360d3392535
Create Date: 2025-12-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'xxxxxxxx'
down_revision: Union[str, Sequence[str], None] = '2025_12_13_1635-6360d3392535'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加角色和权限字段到users表"""
    # 添加角色字段(admin/user)
    op.add_column(
        'users',
        sa.Column('role', sa.String(20), server_default='user', nullable=False, comment="用户角色: admin, user")
    )
    # 添加权限JSONB字段
    op.add_column(
        'users',
        sa.Column('permissions', sa.JSON(), server_default='[]', nullable=False, comment="用户权限列表")
    )
    # 添加索引优化查询
    op.create_index('idx_user_role', 'users', ['role'])


def downgrade() -> None:
    """移除角色和权限字段"""
    # 移除索引
    op.drop_index('idx_user_role')
    # 移除权限字段
    op.drop_column('users', 'permissions')
    # 移除角色字段
    op.drop_column('users', 'role')
```

### **4.3 User模型更新**

**文件**: `server/src/models/user.py`

```python
# 在User类中添加:
role = Column(String(20), default='user', nullable=False, index=True, comment="用户角色: admin, user")
permissions = Column(JSON, default=list, comment="用户权限列表")

# 新增方法:
def has_permission(self, permission: str) -> bool:
    """检查用户是否具有特定权限"""
    return permission in (self.permissions or [])

def has_role(self, role: str) -> bool:
    """检查用户是否具有特定角色"""
    return self.role == role
```

---

## 5. 实施交接

### 变更分类: **Minor**

**Minor级别定义**: 开发团队可以直接实施的变更,无需额外人员介入

### 交付内容

- [ ] 已更新的故事2.5文档
- [ ] 详细变更提案(本文档)
- [ ] 数据库迁移脚本
- [ ] User模型更新方案

### 实施步骤

#### **Phase 1: 数据库更新**
- [ ] 创建数据库迁移脚本
- [ ] 执行数据库迁移
- [ ] 为现有用户添加默认角色('user')

#### **Phase 2: 后端代码更新**
- [ ] 更新User模型
- [ ] 修改JWT令牌生成逻辑(包含role)
- [ ] 实现require_role装饰器
- [ ] 实现require_permission装饰器

#### **Phase 3: 测试**
- [ ] 单元测试: 权限检查函数
- [ ] 集成测试: JWT包含角色信息
- [ ] 端到端测试: 受保护端点权限验证

#### **Phase 4: 文档更新**
- [ ] 更新故事2.5文档
- [ ] 更新API文档
- [ ] 更新架构文档(如需要)

### 实施团队

**主要实施者**: 后端开发团队
**协助者**: 无

**预计完成时间**: 1-2个工作日

---

## 6. 成功标准

### 功能验证
- [ ] 数据库users表成功添加role和permissions字段
- [ ] JWT令牌包含用户角色信息
- [ ] 普通受保护端点只需要认证即可访问
- [ ] 管理员端点正确检查角色(admin)
- [ ] undefined

### 性能验证
- [ ] API响应时间不受影响
- [ ] 权限检查性能提升(无需多表JOIN)

### 文档验证
- [ ] 故事2.5文档已更新为新方案
- [ ] API文档反映新的角色检查机制

---

## 7. 备选方案考虑

### 已评估但拒绝的方案

#### **方案B: 完全移除RBAC**
- **说明**: 完全去掉角色和权限系统
- **拒绝原因**: 项目仍然需要基本的admin/user角色划分

#### **方案C: 使用第三方认证服务**
- **说明**: 集成Auth0、AWS Cognito等第三方服务
- **拒绝原因**: 增加外部依赖,不适合当前Docker化部署策略

---

**审批记录**
- **产品经理**: ________________ [日期]
- **技术负责人**: ________________ [日期]
