# 📋 HR Attendance Viewing Feature - Quick Reference Guide

## ✨ New Feature: "👁️ Davomatni ko'rish" (View Attendance)

### For HR Users

#### Where to Find It
```
Main Menu
  ↓
"👁️ Davomatni ko'rish" button (top right of HR menu)
```

#### How to Use It - Step by Step

**Step 1: Select the Feature**
- Click "👁️ Davomatni ko'rish" from HR menu
- You'll see a numbered list of all employees (1, 2, 3, etc.)

**Step 2: Select an Employee**
- Click the number corresponding to the employee
- Example: "3. Fatima Aziz" → Click "3. Fatima Aziz"
- Wait for date prompt

**Step 3: Enter Date or Month**
- You'll be asked: "📅 Sana (YYYY-MM-DD) yoki oy (YYYY-MM):"
- **For a whole month:** Type `2026-05`
  - Shows all attendance in May 2026
- **For a specific day:** Type `2026-05-24`
  - Shows only that day's record

**Step 4: View Results**
- System displays:
  ```
  📋 *Employee Name Davomati*
  
  📅 *2026-05-24*
    ✅ Keldi: 09:15
    🚪 Ketdi: 18:45
    ⏱️ Ish soati: 9 soat 30 daqiqa
    📊 Holat: normal
  ```

### What Information You Get

For each day of attendance:

| Symbol | Meaning | Example |
|--------|---------|---------|
| 📅 | Date | 2026-05-24 |
| ✅ | Keldi (Arrival) | 09:15 |
| 🚪 | Ketdi (Departure) | 18:45 |
| ⏱️ | Ish soati (Work Hours) | 9 soat 30 daqiqa |
| ⚠️ | Kechikish (Delays) | 15 daqiqa (if late) |
| 📊 | Holat (Status) | normal/sababli/kasal/ta'til |

---

## 💡 Usage Examples

### Example 1: Check May Attendance for Employee #5
```
1. Click: "👁️ Davomatni ko'rish"
2. Click: "5. Rustam Karimov"
3. Type: "2026-05"
4. See: All May 2026 attendance records
```

### Example 2: Check Specific Day for New Employee
```
1. Click: "👁️ Davomatni ko'rish"
2. Click: "1. Karim Naribaev" 
3. Type: "2026-05-20"
4. See: Only May 20 attendance (or "no data" if none)
```

### Example 3: Verify Late Arrivals
```
1. Click: "👁️ Davomatni ko'rish"
2. Click: "8. Dilora Shodmonova"
3. Type: "2026-05"
4. See: All May records with "⚠️ Kechikish" for late arrivals
```

---

## ❌ Common Mistakes & Solutions

### Mistake 1: Wrong Date Format
**You typed:** "May 24, 2026"  
**Error:** "Noto'g'ri format!"  
**Solution:** Use "2026-05-24" instead

### Mistake 2: Wrong Month Format  
**You typed:** "5-24"  
**Error:** "Noto'g'ri format!"  
**Solution:** Use "2026-05" for month

### Mistake 3: No Data Found
**Message:** "❌ Rustam uchun bu davomatda ma'lumot topilmadi!"  
**Reason:** Employee has no attendance record for that date/month  
**Solution:** Try a different date where employee has records

### Mistake 4: Can't Find Employee
**You see:** Numbers 1, 2, 3, 4... but employee is missing  
**Reason:** Sequential numbering updates after deletions  
**Solution:** Count the employees in the list - numbering is always 1,2,3... without gaps

---

## 🎯 Typical HR Use Cases

### Daily Oversight
```
Task: Check who came on time today
1. Go to "👁️ Davomatni ko'rish"
2. Pick employee
3. Enter today's date (2026-05-25)
4. See: Keldi time for today
```

### Monthly Report Preparation
```
Task: Verify attendance for a specific employee this month
1. Go to "👁️ Davomatni ko'rish"
2. Pick the employee
3. Enter "2026-05"
4. See: All attendance for May
5. Count days worked, delays, absences
```

### Late Arrival Investigation
```
Task: Investigate why employee was late
1. Go to "👁️ Davomatni ko'rish"
2. Pick the employee
3. Enter the specific date
4. See: ⚠️ Kechikish (delay amount)
5. Take appropriate action if needed
```

### Probation Period Check
```
Task: Verify new employee's first month attendance
1. Go to "👁️ Davomatni ko'rish"
2. Pick new employee
3. Enter their first month (e.g., "2026-04")
4. See: Complete attendance record
5. Evaluate for confirmation
```

---

## 📊 Data Display Details

### Keldi (Arrival)
- Shows time employee checked in
- Format: HH:MM (24-hour)
- "—" means no check-in recorded

### Ketdi (Departure)
- Shows time employee checked out
- Format: HH:MM (24-hour)
- "—" means no check-out recorded

### Ish Soati (Work Hours)
- Calculated from Ketdi - Keldi
- Format: "X soat Y daqiqa"
- Only shown if both Keldi and Ketdi exist

### Kechikish (Delays)
- Minutes late from scheduled start time
- Only shown if > 0
- Helps identify patterns of tardiness

### Holat (Status)
- **normal:** Regular working day
- **sababli:** With valid reason
- **kasal:** Sick leave
- **ta'til:** Vacation/holiday

---

## 🔄 Going Back

**To return to HR Menu:**
- After viewing results, click "👔 HR menu" button
- Or use "☰ Menu" → "👔 HR menu"

**To try another employee:**
- Click "👔 HR menu" 
- Click "👁️ Davomatni ko'rish" again
- Select different employee

---

## ⚙️ System Behavior

### Sequential Employee Numbering
- Employees always numbered 1, 2, 3, 4...
- **No gaps** even if employees were deleted
- **Example:** If employee #8 is deleted, remaining employees become 1-12 (not 1-7, 9-13)

### Date Filtering
- Both month and specific date searches work
- "2026-05" shows all 31 days of May (whichever exist)
- "2026-05-24" shows only that one day
- No data = honest "not found" message

### Performance
- Fast response for monthly queries
- Usually shows within 1-2 seconds
- Can handle large attendance histories

---

## 🚫 What This Feature DOES NOT Do

- ❌ Edit or change attendance records (use Manual davomat for that)
- ❌ View employee personal details
- ❌ Generate formal reports (use Hisobot for that)
- ❌ Delete or modify records
- ❌ Show future predictions

---

## ✅ What This Feature DOES Do

- ✅ View historical attendance data
- ✅ Filter by month or specific date
- ✅ See arrival and departure times
- ✅ Identify delays and work hours
- ✅ Help with HR decision-making
- ✅ Support attendance verification

---

## 🎓 Tips for Best Results

1. **Know the employee's name** - Can't search by ID, must select from list
2. **Use consistent date format** - Always YYYY-MM-DD or YYYY-MM
3. **Check monthly first** - Then drill down to specific days if needed
4. **Note the statuses** - "sababli", "kasal" explain absences
5. **Cross-reference delays** - Compare with employee's schedule start time

---

## 📞 Getting Help

### If Feature Not Showing
- Verify your role is "HR" (not admin/employee)
- Try /start to refresh menu
- Wait for bot to respond (Railway deploy in progress)

### If Date Not Working
- Check format exactly: YYYY-MM-DD
- Don't use slashes: ❌ 2026/05/24, ✅ 2026-05-24
- Don't use month names: ❌ "May", ✅ "2026-05"

### If Employee List Looks Wrong
- Numbering updates after deletions
- Count the list - should be 1,2,3... without gaps
- If employee not in list, they may be deleted/inactive

---

## 🎉 You're All Set!

The "👁️ Davomatni ko'rish" feature is ready to use. Happy HR work! 

**Happy HR auditing!** 👁️📋

---

*Feature Available Since: May 25, 2026*  
*Status: Production Ready*  
*Last Updated: 14:55 UTC*
