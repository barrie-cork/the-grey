# Search Strategy Implementation Tasks

**Phase:** 3 - Dynamic Features Complete  
**Status:** Production Ready - Core Implementation Complete  
**Reference Implementation:** `apps/review_manager` (Follow established patterns)  
**Start Date:** 2025-05-31  
**Last Updated:** 2025-05-31  

## Task Overview

This document tracks the implementation of the Search Strategy Builder app following the core requirements and user stories. All tasks follow the architectural patterns established in the Review Manager reference implementation.

## 📈 Progress Summary

**Phase 1 Complete:** Foundation & Core Models
- ✅ **Task 1-3 Completed:** App structure, models, and review manager integration
- ✅ **Database:** SearchStrategy and SearchQuery models implemented with PostgreSQL ArrayField and JSONField
- ✅ **Integration:** Seamless workflow integration with review_manager app
- ✅ **Security:** Following established security patterns from review_manager
- ✅ **Testing:** All models and integration tested successfully

**Phase 2 Complete:** Forms & User Interface
- ✅ **Task 4 Completed:** SearchStrategy Forms with comprehensive validation and testing
- ✅ **Task 5 Completed:** Core Views Implementation with security and API endpoints
- ✅ **Task 6 Completed:** Enhanced Templates & Frontend with real-time features and professional UI

**Current Status:** Phase 3 Dynamic Features Complete - Production Ready Core Implementation

**Phase 3 Complete:** Dynamic Features & Enhanced UX
- ✅ **Task 7 Completed:** Advanced Query Generation Logic with multi-domain support and dynamic PIC interface
- ✅ **Enhanced UI:** Tag-based input system for PIC terms and organization domains  
- ✅ **Smart Query Logic:** N domains + general search = N+1 total queries with proper Boolean operators
- ✅ **File Type Optimization:** Simplified to PDF + Word documents with automatic .doc/.docx expansion

**Key Achievements:**
- Complete PIC framework model implementation using PostgreSQL ArrayField
- Advanced query generation with support for Google Search and Scholar
- Comprehensive session workflow integration with status validation
- Enhanced dashboard and session detail pages with strategy information
- Admin interface following review_manager patterns
- Comprehensive SearchStrategy forms with validation and security features (Task 4)
- Complete test suite with 17 test cases and 100% form coverage
- Full Django CBV implementation with security decorators and audit logging (Task 5)
- API endpoints for real-time query preview and strategy validation
- 30+ view tests covering all functionality and edge cases
- **Manual Testing Verified:** All core functionality working in development server

---

## 🏗️ Phase 1: Foundation & Core Models (High Priority)

### Task 1: App Structure Setup ✅ COMPLETED
- [x] Create `apps/search_strategy` Django app
- [x] Set up directory structure following review_manager pattern:
  - [x] Create `models.py`, `views.py`, `forms.py`, `urls.py`
  - [x] Create `static/search_strategy/` with css/js subdirectories
  - [x] Create `templates/search_strategy/` directory
  - [x] Create `tests/` directory with organized test files
- [x] Configure app in `settings/base.py` INSTALLED_APPS
- [x] Create initial URL routing in main `urls.py`

### Task 2: SearchStrategy Model Implementation ✅ COMPLETED
- [x] Implement core SearchStrategy model with UUID primary key
  - [x] Add session foreign key to SearchSession (review_manager integration)
  - [x] Add user foreign key using `settings.AUTH_USER_MODEL` pattern
  - [x] Add PIC framework fields:
    - [x] `population_terms` (ArrayField for population concepts)
    - [x] `interest_terms` (ArrayField for interest/intervention concepts) 
    - [x] `context_terms` (ArrayField for context/setting concepts)
  - [x] Add domain selection field (JSONField with search_config)
  - [x] Add file type selection field (JSONField for multiple types)
  - [x] Add generated query preview methods (generate_base_query, generate_full_query)
  - [x] Add timestamps (created_at, updated_at)
  - [x] Add validation methods for PIC framework completeness
  - [x] Add SearchQuery model for query storage
- [x] Create database migration
- [x] Add model to admin interface following review_manager patterns

### Task 3: Review Manager Integration ✅ COMPLETED
- [x] Update SearchSession model in review_manager:
  - [x] Add OneToOne relationship to SearchStrategy via reverse foreign key
  - [x] Update `can_transition_to` method to check strategy completion
  - [x] Add `has_strategy()` and `strategy_has_terms()` methods
  - [x] Enhanced stats property with strategy information
- [x] Update review_manager dashboard:
  - [x] Add "Define Strategy" action button for draft sessions
  - [x] Update session card to show strategy status
  - [x] Add navigation to search strategy from session detail
  - [x] Enhanced session statistics with PIC framework breakdown
- [x] Create URL routing between apps using proper URL patterns

---

## 🎨 Phase 2: Forms & User Interface (High Priority)

### Task 4: SearchStrategy Forms ✅ COMPLETED
- [x] Create SearchStrategyForm using Django ModelForm:
  - [x] Implement PIC framework input fields with proper widgets (TagWidget for comma-separated input)
  - [x] Add domain selection using ChoiceField with predefined options (NICE, WHO, NHS, etc.)
  - [x] Add file type filtering using MultipleChoiceField (PDF, DOC, HTML, etc.)
  - [x] Add form validation for required PIC categories (at least one term required)
  - [x] Add clean methods for term validation and formatting (length, character validation, deduplication)
  - [x] Implement server-side validation with helpful error messages (XSS prevention, domain validation)
- [x] Create SearchStrategyUpdateForm for editing existing strategies (with activity logging)
- [x] Add CSRF protection and security validation following review_manager patterns
- [x] Add comprehensive test suite (17 tests covering all functionality)
- [x] Add SearchStrategyValidationMixin for reusable validation logic

### Task 5: Core Views Implementation ✅ COMPLETED
- [x] Create SearchStrategyCreateView:
  - [x] Use Django CreateView with session ownership validation
  - [x] Apply security decorators (@login_required, @owns_session, @audit_action)
  - [x] Validate session is in 'draft' status
  - [x] Redirect to detail view after successful creation
  - [x] Handle existing strategy redirects properly
- [x] Create SearchStrategyUpdateView:
  - [x] Use Django UpdateView with ownership validation
  - [x] Restrict editing to draft sessions only
  - [x] Apply session status validation decorators
  - [x] Integrate with activity logging
- [x] Create SearchStrategyDetailView:
  - [x] Display complete strategy with generated query preview
  - [x] Show PIC framework breakdown with statistics
  - [x] Add edit/save actions based on permissions
  - [x] Generate next action suggestions based on session status
- [x] Create API endpoints:
  - [x] Query preview API for real-time query generation
  - [x] Strategy validation API for completeness checking
  - [x] Rate limiting and security on all endpoints
- [x] Create comprehensive test suite (30 tests covering all functionality)
- [x] Create basic templates for Phase 2 compatibility
- [x] Manual testing verification:
  - [x] Search strategy creation and editing workflow
  - [x] Form validation and error handling
  - [x] Query generation and preview functionality
  - [x] Security and permission controls
  - [x] Integration with review_manager workflow

### Task 6: Templates & Frontend ✅ COMPLETED
- [x] Create base template extending review_manager patterns:
  - [x] Use consistent navigation and styling
  - [x] Implement responsive design for desktop and mobile
  - [x] Add breadcrumb navigation across all views
- [x] Create search strategy form template:
  - [x] Build PIC framework input interface with clear sections
  - [x] Add domain selection with descriptions
  - [x] Implement file type checkboxes with visual indicators
  - [x] Add form validation display with helpful error messages
  - [x] Real-time term counting and progress tracking
  - [x] Live query preview panel with API integration
- [x] Create strategy detail/preview template:
  - [x] Display PIC categories with color-coded term lists
  - [x] Show generated query preview in formatted view
  - [x] Add action buttons for edit/save/execute
  - [x] Strategy validation with detailed feedback
  - [x] Export functionality (JSON, CSV, TXT formats)
  - [x] Click-to-copy PIC terms with visual feedback
- [x] Enhanced JavaScript functionality:
  - [x] Real-time form validation and query preview (strategy_form.js)
  - [x] Interactive strategy detail features (strategy_detail.js)
  - [x] AJAX integration with existing API endpoints
  - [x] Debounced input handling for performance
- [x] Custom CSS styling (474 lines):
  - [x] PIC framework term styling with categories
  - [x] Progress bars and visual indicators
  - [x] Responsive design and accessibility
  - [x] Print styles and animation effects

---

## ⚡ Phase 3: Dynamic Features (Medium Priority)

### Task 7: Query Generation Logic ✅ COMPLETED
- [x] ✅ Implement automatic query generation using Python string manipulation:
  - [x] ✅ Built Boolean logic for combining terms within categories (OR within, AND between)
  - [x] ✅ Implemented cross-category combination logic with proper precedence
  - [x] ✅ Added domain-specific query formatting with site: restrictions
  - [x] ✅ Included file type filters in generated queries (PDF + Word .doc/.docx)
  - [x] ✅ Enhanced to support N custom domains + optional general search = N+1 queries
- [x] ✅ Query generation integrated into SearchStrategy model methods
- [x] ✅ Query validation and URL generation for Google/Scholar searches

**Implementation Details:**
- **Dynamic PIC Interface**: Tag-based input for Population, Interest, Context terms
- **Custom Domain Management**: Dynamic URL input with tag interface for organization domains
- **Smart Query Logic**: `(pop1 OR pop2) AND (int1 OR int2) AND (ctx1 OR ctx2)`
- **File Type Expansion**: "doc" selection includes both .doc and .docx in queries
- **Multi-Domain Support**: Each domain creates separate `site:domain.com` query
- **Query Preview**: Real-time generation and display of search queries

### Task 8: Real-time Preview with AJAX
- [ ] Create AJAX endpoint for query preview:
  - [ ] Implement Django AJAX view for real-time updates
  - [ ] Add JSON response formatting
  - [ ] Include error handling and validation responses
- [ ] Add JavaScript for real-time preview:
  - [ ] Monitor form input changes
  - [ ] Send AJAX requests for query generation
  - [ ] Update preview section without page reload
  - [ ] Handle loading states and error messages
- [ ] Implement debounced input handling for performance

### Task 9: Validation & Error Handling
- [ ] Implement comprehensive Django form validation:
  - [ ] Validate PIC framework completeness
  - [ ] Check term format and content requirements
  - [ ] Validate domain selection consistency
  - [ ] Ensure file type compatibility
- [ ] Add helpful error messages and guidance:
  - [ ] Provide specific validation feedback
  - [ ] Include examples and tips for form completion
  - [ ] Add progress indicators for required fields
- [ ] Create recovery mechanisms for invalid states

---

## 🔗 Phase 4: Workflow Integration (Medium Priority)

### Task 10: Session Status Transitions
- [ ] Update review_manager workflow to integrate search strategy:
  - [ ] Modify 'draft' → 'strategy_ready' transition logic
  - [ ] Add validation that strategy is complete before transition
  - [ ] Update dashboard navigation based on strategy status
- [ ] Create navigation flow:
  - [ ] "Define Strategy" button from session detail/dashboard
  - [ ] "Save & Continue" to mark session as strategy_ready
  - [ ] "Back to Session" navigation with unsaved changes warning
- [ ] Implement strategy completion validation before advancing workflow

### Task 11: URL Routing & Navigation
- [ ] Create comprehensive URL patterns:
  - [ ] `/review/session/{id}/strategy/` - strategy for specific session
  - [ ] `/review/session/{id}/strategy/edit/` - edit existing strategy
  - [ ] `/review/session/{id}/strategy/preview/` - preview generated queries
- [ ] Add navigation integration:
  - [ ] Update review_manager templates with strategy links
  - [ ] Add breadcrumb navigation across apps
  - [ ] Implement "Next Step" guidance after strategy completion
- [ ] Use safe_reverse pattern for future app compatibility

---

## 🧪 Phase 5: Testing & Quality Assurance (High Priority)

### Task 12: Comprehensive Testing
- [ ] Create test structure following review_manager patterns:
  - [ ] `tests/test_models.py` - Model validation and relationships
  - [ ] `tests/test_forms.py` - Form validation and security
  - [ ] `tests/test_views.py` - View functionality and permissions
  - [ ] `tests/test_integration.py` - Cross-app integration tests
- [ ] Implement security testing:
  - [ ] Session ownership validation tests
  - [ ] CSRF protection verification
  - [ ] Input sanitization and XSS prevention
  - [ ] Permission boundary testing
- [ ] Add performance testing:
  - [ ] Query generation performance benchmarks
  - [ ] AJAX response time validation
  - [ ] Form validation efficiency tests
- [ ] Create integration tests with review_manager:
  - [ ] Session workflow transition testing
  - [ ] Navigation flow validation
  - [ ] Data consistency verification

### Task 13: Quality Assurance
- [ ] Code review and optimization:
  - [ ] Follow review_manager coding standards
  - [ ] Implement consistent error handling
  - [ ] Add comprehensive docstrings and comments
  - [ ] Optimize database queries and form performance
- [ ] Documentation creation:
  - [ ] Update main project documentation
  - [ ] Create search_strategy specific docs
  - [ ] Add user guide sections for search strategy
- [ ] Accessibility and usability testing:
  - [ ] Keyboard navigation testing
  - [ ] Screen reader compatibility
  - [ ] Mobile responsiveness validation

---

## 📋 Phase 6: Documentation & Deployment (Low Priority)

### Task 14: Documentation
- [ ] Create comprehensive documentation following review_manager structure:
  - [ ] `docs/features/search-strategy/search-strategy-api.md`
  - [ ] `docs/features/search-strategy/search-strategy-architecture.md`
  - [ ] `docs/features/search-strategy/search-strategy-user-guide.md`
- [ ] Update project-level documentation:
  - [ ] Update main README with search strategy features
  - [ ] Add search strategy section to User Stories documentation
  - [ ] Update architecture diagrams and workflow documentation
- [ ] Create developer onboarding documentation for search strategy patterns

### Task 15: Final Integration & Testing
- [ ] End-to-end workflow testing:
  - [ ] Complete user journey from session creation through strategy definition
  - [ ] Verify all navigation flows work correctly
  - [ ] Test error scenarios and recovery paths
- [ ] Performance optimization:
  - [ ] Database query optimization
  - [ ] Frontend asset optimization
  - [ ] AJAX performance tuning
- [ ] Deployment preparation:
  - [ ] Production settings configuration
  - [ ] Static file collection testing
  - [ ] Migration validation

---

## 📊 Success Criteria

- [ ] **Functional Requirements Met**: All user stories implemented and tested
- [ ] **Integration Complete**: Seamless workflow with review_manager
- [ ] **Security Standards**: Following review_manager security patterns
- [ ] **Test Coverage**: Minimum 95% test coverage following project standards
- [ ] **Documentation Complete**: Full documentation suite created
- [ ] **Performance Validated**: Acceptable response times for all features
- [ ] **User Experience**: Intuitive interface following established UI patterns

---

## 🎯 Next Phase Preparation

Upon completion of Search Strategy Builder:
- [ ] **SERP Execution App**: Background search execution (strategy_ready → executing)
- [ ] **Results Manager App**: Search result processing (executing → processing → ready_for_review)
- [ ] **Review Results App**: Manual review interface (ready_for_review → in_review → completed)

---

**Implementation Notes:**
- Follow review_manager app as the reference for all patterns
- Use UUID primary keys consistently with custom User model
- Implement comprehensive security following established decorators
- Maintain audit trail integration with SessionActivity logging
- Use Django best practices for forms, views, and templates
- Test thoroughly before advancing to next phase

**Status:** Ready for implementation  
**Estimated Duration:** 2-3 weeks  
**Dependencies:** Review Manager app (completed ✅)