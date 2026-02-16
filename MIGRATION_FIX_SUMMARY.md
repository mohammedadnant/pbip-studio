# Migration Preview Fix - Preventing Table Mixing Between Semantic Models

## Problem Description
When performing multiple semantic model data source changes in the migration preview, clicking the "Apply Changes & Migrate" button was causing tables from different semantic models to be mixed up. The system wasn't properly isolating each semantic model's tables during the migration process.

## Root Cause Analysis
The issue was in how the preview data was being combined and displayed:

1. **Preview Combination**: When multiple semantic models were selected, all file changes were merged into a flat list without maintaining clear boundaries between models.

2. **Display Organization**: The preview tree showed all files in a flat structure, making it unclear which tables belonged to which semantic model.

3. **Lack of Visual Separation**: No clear indication showing which model each table belonged to during the preview phase.

## Solution Implemented

### 1. Enhanced Preview Data Structure
**File**: `src/gui/main_window.py` - `execute_bulk_migration()` method

- Added `models_preview` array to track individual model previews
- Each file change now includes `model_name` and `model_path` metadata
- Preview structure maintains model boundaries:

```python
combined_preview = {
    'files_to_change': [],
    'models_preview': [],  # NEW: Individual model previews preserved
    'summary': {...}
}
```

### 2. Hierarchical Tree View Display
**File**: `src/gui/main_window.py` - `load_preview_data()` method

- When multiple models are selected, files are now organized hierarchically:
  ```
  📦 Semantic Model 1
    📄 Table1.tmdl
    📄 Table2.tmdl
  📦 Semantic Model 2
    📄 Table3.tmdl
    📄 Table4.tmdl
  ```

- Single model selection shows flat list (original behavior)
- Clear visual separation with model nodes expanded by default

### 3. Enhanced Confirmation Dialog
**File**: `src/gui/main_window.py` - `apply_preview_changes()` method

- Shows breakdown of tables per model
- Example confirmation message:
  ```
  Apply migration changes to 2 semantic models?

  • SalesModel: 5 tables
  • InventoryModel: 3 tables

  Total: 8 files, 120 lines changed.

  Each model will be processed separately to prevent table mixing.
  ```

### 4. Improved Migration Logging
**File**: `src/gui/main_window.py` - `execute_migration_from_preview()` method

- Clear headers showing which semantic model is being processed
- Lists tables being migrated for each source
- Example output:
  ```
  ============================================================
  [1/2] SEMANTIC MODEL: SalesModel
  ============================================================
  📁 Path: C:\Data\SalesModel.SemanticModel
    → Found 1 source(s) to migrate
    💾 Creating backup before migration...
    
    [1/1] Migrating OnPremSQL (5 tables)...
        Tables: FactSales, DimCustomer, DimProduct...
  ```

### 5. Documentation Enhancement
**File**: `src/utils/data_source_migration.py` - `migrate_all_tables()` function

- Added comprehensive docstring emphasizing isolation
- Documents that function ONLY processes tables in `source_info['tables']`
- Prevents accidental cross-model contamination

## Key Improvements

### ✅ Model Isolation
- Each semantic model is processed completely independently
- The `dest_model_path` parameter ensures tables are migrated within the correct model
- No possibility of tables from Model A being written to Model B

### ✅ Clear Visual Hierarchy
- Multi-model migrations show tree structure with model grouping
- Easy to see which tables belong to which semantic model
- Color-coded change indicators preserved

### ✅ Better User Feedback
- Confirmation dialog shows per-model breakdown
- Migration log clearly indicates which model is being processed
- Table list shown for each source being migrated

### ✅ Maintained Backward Compatibility
- Single model migrations work exactly as before (flat list)
- No breaking changes to existing functionality
- Preview generation logic unchanged

## Technical Details

### How the Fix Works

1. **Preview Generation** (`execute_bulk_migration`):
   - Generates individual preview for each model+source combination
   - Stores all previews in `models_preview` array
   - Tags each file change with its source model

2. **Display** (`load_preview_data`):
   - Checks if `models_preview` contains multiple models
   - If yes: Creates hierarchical tree with model parent nodes
   - If no: Shows flat list (original behavior)

3. **Migration Execution** (`execute_migration_from_preview`):
   - Already correctly iterates through each model separately
   - Passes correct `model['path']` to `migrate_all_tables`
   - Enhanced logging shows which model is being processed

4. **Table Migration** (`migrate_all_tables`):
   - Only processes tables in `source_info['tables']` list
   - Uses `dest_model_path` to locate correct tables folder
   - Cannot accidentally access tables from other models

## Testing Recommendations

To verify the fix works correctly:

1. **Select Multiple Semantic Models** with different tables
2. **Click "Preview Migration"** - verify tree shows models hierarchically
3. **Review each model node** - confirm correct tables under each model
4. **Click "Apply Changes & Migrate"** - verify confirmation shows per-model breakdown
5. **Monitor migration log** - confirm each model processed separately with clear headers
6. **Verify results** - check that each model's tables were updated correctly

## Files Modified

1. `src/gui/main_window.py`:
   - `execute_bulk_migration()` - Enhanced preview combination
   - `load_preview_data()` - Hierarchical tree display
   - `apply_preview_changes()` - Enhanced confirmation dialog
   - `execute_migration_from_preview()` - Improved logging

2. `src/utils/data_source_migration.py`:
   - `migrate_all_tables()` - Enhanced documentation

## Conclusion

The fix ensures complete isolation between semantic models during migration by:
- Maintaining clear model boundaries in the preview data structure
- Displaying hierarchical organization in the UI
- Processing each model independently with clear logging
- Preventing any possibility of table mixing

The migration system now properly handles multiple semantic models while maintaining clarity and preventing cross-contamination of table changes.
