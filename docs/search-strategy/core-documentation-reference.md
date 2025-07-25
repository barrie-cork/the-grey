# Core Documentation Reference for Search Strategy Implementation

## Essential Documents for Task Implementation

### 1. **Review Manager Reference Implementation**
**File:** `apps/review_manager/docs/architecture.md`  
**Why:** Complete architectural patterns, security decorators, model structures, and development standards to follow exactly.

### 2. **Custom User Model Requirements** 
**File:** `CUSTOM_USER_ALERT.md`  
**Why:** Critical UUID patterns and `get_user_model()` usage - breaks everything if not followed.

### 3. **Search Strategy Requirements**
**File:** `docs/User_Stories_and_Requirements.md` (Search Strategy section)  
**Why:** Exact functional requirements, PIC framework specification, and Django implementation details.

### 4. **Project Architecture**
**File:** `docs/ARCHITECTURE.MD`  
**Why:** Overall system design, app relationships, and integration points with review_manager workflow.

### 5. **Review Manager API Patterns**
**File:** `apps/review_manager/docs/api.md`  
**Why:** Security patterns, AJAX implementation, URL routing, and response formats to maintain consistency.

### 6. **Development Standards**
**File:** `DEVELOPMENT_GUIDE.md`  
**Why:** Code quality standards, testing requirements, and Django best practices established for the project.

---

**Critical Success Factor:** Follow review_manager patterns exactly - it's the reference implementation for all architectural decisions, security patterns, and code quality standards.