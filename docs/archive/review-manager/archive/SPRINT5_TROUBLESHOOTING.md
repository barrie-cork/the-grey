# Sprint 5 Troubleshooting Guide

## 🚨 Common Sprint 5 Errors and Solutions

### Issue 1: ImportError - Cannot import UserFeedbackMixin

**Error:** `ImportError: cannot import name 'UserFeedbackMixin' from 'apps.review_manager.mixins'`

**Cause:** The mixins.py file may have syntax errors or the class definition is incomplete.

**Solution:**
1. Check `apps/review_manager/mixins.py` for syntax errors
2. Ensure the class starts with `class UserFeedbackMixin:`
3. Run: `python -m py_compile apps/review_manager/mixins.py`

### Issue 2: Template Syntax Errors

**Error:** Template errors in dashboard.html

**Solution:**
1. Ensure `{% load static %}` is at the top of dashboard.html
2. Check all `{% static %}` tags have proper quotes
3. Verify template inheritance with `{% extends %}`

### Issue 3: Static Files Not Loading

**Error:** CSS/JS files return 404 errors

**Solution:**
1. Run: `python manage.py collectstatic`
2. Check `STATIC_URL` and `STATICFILES_DIRS` in settings
3. Ensure static files are in correct directories

### Issue 4: Database Errors

**Error:** Database connection or migration errors

**Solution:**
1. Check database settings in `.env` file
2. Run: `python manage.py makemigrations`
3. Run: `python manage.py migrate`

### Issue 5: URL Resolution Errors

**Error:** `NoReverseMatch` errors

**Solution:**
1. Check URL patterns in `apps/review_manager/urls.py`
2. Verify app is included in main `thesis_grey_project/urls.py`
3. Ensure app_name is set correctly

## 🛠️ Quick Fix Commands

Run these commands in order:

```bash
# 1. Activate virtual environment
venv\Scripts\activate

# 2. Install/update requirements
pip install -r requirements.txt

# 3. Check Django configuration
python manage.py check

# 4. Apply migrations
python manage.py makemigrations
python manage.py migrate

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Test the server
python manage.py runserver
```

## 🔧 Manual Fixes

### Fix UserFeedbackMixin Request Attribute Error

If you get `AttributeError: 'UserFeedbackMixin' object has no attribute 'request'`:

Add this to any view using UserFeedbackMixin:

```python
class YourView(LoginRequiredMixin, UserFeedbackMixin, ListView):
    # Your view code
    pass
```

Make sure UserFeedbackMixin comes AFTER Django's view mixins.

### Fix Static Files Development

Add to `settings/local.py`:

```python
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
```

### Fix JavaScript Console Errors

Check browser console for:
- `ReferenceError` - missing JavaScript dependencies
- `TypeError` - incorrect method calls
- `SyntaxError` - JavaScript syntax issues

## 📋 Verification Checklist

After fixes, verify:

- [ ] Dashboard loads without errors
- [ ] CSS styles are applied
- [ ] JavaScript functionality works
- [ ] Filtering and search work
- [ ] Session creation works
- [ ] No console errors in browser
- [ ] Responsive design works on mobile

## 🆘 Getting More Help

If issues persist:

1. Check browser developer console for JavaScript errors
2. Check Django logs for Python errors
3. Use the diagnostic script: `python sprint5_fix.py`
4. Verify all Sprint 4 features still work
5. Compare your implementation with the PRD requirements

## 🎯 Sprint 5 Success Criteria

Your Sprint 5 is working correctly when:

✅ **Advanced Filtering (Task 25)**
- Search box filters sessions by title/description
- Status filter dropdown works
- Date range filter works
- Sort options work
- Filters can be combined

✅ **Responsive CSS (Task 26)**
- Dashboard looks good on mobile/tablet/desktop
- Touch targets are large enough on mobile
- Text is readable at all screen sizes

✅ **Contextual Help (Task 27)**
- Help tooltips appear on hover
- Help panel can be opened/closed
- Help content is relevant to current page

✅ **Breadcrumb Navigation (Task 28)**
- Breadcrumbs show current location
- Breadcrumbs are accessible via keyboard
- Breadcrumbs update dynamically

✅ **User Feedback (Task 29)**
- Success messages appear after actions
- Error messages are helpful
- Messages auto-dismiss after time

✅ **Enhanced JavaScript (Task 30)**
- No JavaScript console errors
- Interactive elements respond smoothly
- Keyboard shortcuts work (Ctrl+F for search)
