# Review Manager Documentation

## 📍 **Primary Documentation Location**

**The comprehensive Review Manager documentation is located in:**

```
apps/review_manager/docs/
├── api.md           # Complete API documentation (851 lines)
├── architecture.md  # Technical architecture with migration details (539+ lines)
├── deployment.md    # Production deployment guide (1255 lines)
└── user-guide.md    # End-user documentation (535 lines)
```

## 📚 **What's in Each Document**

### **For Developers**
- **`architecture.md`** - Code patterns, security implementation, migration details, development guidelines
- **`api.md`** - Complete API reference with examples, security features, response formats

### **For DevOps/Deployment**
- **`deployment.md`** - Complete production deployment guide with PostgreSQL, Redis, Nginx, security

### **For End Users**  
- **`user-guide.md`** - How to use the Review Manager interface, workflow explanations

## 📁 **This Directory Contains**

- **`UUID_MIGRATION_FIX.md`** - Historical record of UUID migration issue and resolution
- **`review-manager-prd.md`** - Product Requirements Document
- **`tasks-review-manager-implementation.md`** - Development task tracking
- **`archive/`** - Historical documents (sprint reports, troubleshooting, outdated guides)

## ⚡ **Quick Start for Developers**

1. **Architecture Overview**: Read `apps/review_manager/docs/architecture.md`
2. **API Reference**: See `apps/review_manager/docs/api.md` 
3. **Critical Migration Info**: Check `UUID_MIGRATION_FIX.md` for UUID requirements
4. **Development Patterns**: Follow examples in `architecture.md`

## 🚨 **Critical Information**

- **Custom User Model**: Always use `get_user_model()` - see architecture.md
- **UUID Primary Keys**: All models use UUIDs - see UUID_MIGRATION_FIX.md
- **Security Patterns**: Comprehensive security implementation - see architecture.md
- **Field Migration**: SessionActivity fields were renamed - see architecture.md

---

**Status:** Production Ready ✅  
**Version:** 1.0.0  
**Test Coverage:** 381+ tests (95.8% coverage)  
**Security:** Enterprise-grade with audit trail