# 📂 CSV File Format Guide

## Required CSV Structure

### Header Row (Required)
```csv
Task_Hours,Idle_Hours,Social_Media_Usage,Break_Frequency,Tasks_Completed
```

### Column Descriptions

| Column Name | Data Type | Description | Example Values |
|------------|-----------|-------------|----------------|
| `Task_Hours` | Decimal | Hours spent on productive tasks | 0-24 |
| `Idle_Hours` | Decimal | Hours of unproductive time | 0-24 |
| `Social_Media_Usage` | Decimal | Hours spent on social media | 0-24 |
| `Break_Frequency` | Integer | Number of breaks taken | 0-20+ |
| `Tasks_Completed` | Integer | Number of tasks finished | 0-50+ |

---

## Sample CSV File

```csv
Task_Hours,Idle_Hours,Social_Media_Usage,Break_Frequency,Tasks_Completed
6,1,0.5,4,8
8,0.5,1,3,12
4,3,2,8,3
7,1,1.5,5,10
5,2,3,6,5
3,4,4,10,2
9,0,0.5,2,15
6.5,1.5,1,4,9
7.5,0.5,0.5,3,11
5.5,2,2.5,7,6
```

---

## Data Validation Rules

### ✅ Valid Data
- **Numeric values** (integers or decimals)
- **Positive numbers** (>= 0)
- **Reasonable ranges**:
  - Hours: 0-24
  - Breaks: 0-20
  - Tasks: 0-50

### ❌ Invalid Data
- Text values (except headers)
- Negative numbers
- Empty cells (will default to 0)
- Missing required columns

---

## How to Create Your CSV

### Method 1: Download Template
1. Go to **Upload CSV** page
2. Click **"Download Template"** button
3. Edit the file with your data
4. Save and upload

### Method 2: Create in Excel
1. Open Microsoft Excel
2. Add headers in first row:
   ```
   Task_Hours | Idle_Hours | Social_Media_Usage | Break_Frequency | Tasks_Completed
   ```
3. Enter your data in rows below
4. Save as CSV:
   - File → Save As
   - Choose "CSV (Comma delimited) (*.csv)"

### Method 3: Create in Google Sheets
1. Open Google Sheets
2. Add headers and data
3. Download as CSV:
   - File → Download → Comma Separated Values (.csv)

### Method 4: Text Editor
1. Open Notepad or any text editor
2. Copy sample format above
3. Save with `.csv` extension

---

## Example Scenarios

### Highly Productive User
```csv
Task_Hours,Idle_Hours,Social_Media_Usage,Break_Frequency,Tasks_Completed
9,0.5,0.5,2,15
```
**Expected Score:** ~85-95 (Highly Productive)

### Moderately Productive User
```csv
Task_Hours,Idle_Hours,Social_Media_Usage,Break_Frequency,Tasks_Completed
6,1.5,1.5,5,7
```
**Expected Score:** ~50-75 (Moderately Productive)

### Fake Productivity User
```csv
Task_Hours,Idle_Hours,Social_Media_Usage,Break_Frequency,Tasks_Completed
3,4,3,10,2
```
**Expected Score:** ~20-45 (Fake Productivity)

---

## Upload Process

1. **Prepare CSV file** following the format above
2. Go to **Upload CSV** page
3. **Drag and drop** file or click to browse
4. **Preview** first 5 rows to verify
5. Click **"Analyze CSV"**
6. View **batch results** with color-coded cards
7. **Export results** as CSV if needed

---

## Troubleshooting

### Issue: "CSV must contain Task_Hours and Idle_Hours columns"
**Solution:** Ensure column headers match exactly (case-insensitive, underscores important)

### Issue: File not uploading
**Solution:** 
- Check file extension is `.csv`
- Ensure file is not corrupted
- Try re-saving from Excel/Sheets

### Issue: Unexpected scores
**Solution:**
- Verify data is numeric
- Check for negative values
- Ensure values are in reasonable ranges

### Issue: Empty results
**Solution:**
- Ensure file has data rows (not just headers)
- Check for blank lines at end of file
- Remove any special characters

---

## Best Practices

✅ **Use consistent formatting**
✅ **Include all 5 required columns**
✅ **Use decimal points for fractional hours** (e.g., 1.5, not 1,5)
✅ **No spaces in column names**
✅ **Test with small file first** (5-10 rows)
✅ **Keep backup of original data**

---

## Quick Tips

💡 **Missing columns:** Optional columns (Social_Media_Usage, Break_Frequency, Tasks_Completed) will default to 0

💡 **Extra columns:** Additional columns will be ignored

💡 **Large files:** Application can handle 100+ rows efficiently

💡 **Export results:** Always export analysis results for record-keeping

---

**Need Help?**
- Download the template from Upload CSV page
- Follow the example format exactly
- Contact support if issues persist
