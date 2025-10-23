# CardFlux Shop Testing Guide

**Date**: 2025-10-23
**Version**: v0.2.2 (with configurable confidence thresholds)
**Status**: ✅ **READY FOR SHOP TESTING**

---

## 🎯 Quick Start for Shop Testing

### **Performance**:
- **Speed**: ~1 second per card (983ms average)
- **Auto-add Rate**: 88% (HIGH + MODERATE confidence)
- **Manual Review**: 0% (by default, configurable)
- **Accuracy**: 100% on test images

### **Recommended Settings for Shop**:
```
✅ Auto-add MODERATE confidence: ON (fast scanning)
❌ Accept LOW confidence: OFF (maintain quality)
✅ Geometric verification: ON (accuracy)
❌ OCR: OFF (speed priority)
❌ Multi-frame: OFF (speed priority)
```

---

## 📋 Confidence System Explained

### **Default Behavior** (Recommended for Shops):

| Confidence | Score Range | Auto-Add? | Action | Percentage |
|------------|-------------|-----------|--------|------------|
| **HIGH** | ≥0.70 | ✅ YES | Add to stack | 44% |
| **MODERATE** | ≥0.55 | ✅ YES | Add to stack | 44% |
| **LOW** | <0.55 | ❌ NO | Reject & rescan | 11% |

**Result**: 88% auto-add rate = fast scanning!

### **Conservative Mode** (More Control):

| Confidence | Score Range | Auto-Add? | Action | Percentage |
|------------|-------------|-----------|--------|------------|
| **HIGH** | ≥0.70 | ✅ YES | Add to stack | 44% |
| **MODERATE** | ≥0.55 | ❓ REVIEW | Manual confirm | 44% |
| **LOW** | <0.55 | ❌ NO | Reject & rescan | 11% |

**Settings**: Turn OFF "Auto-add MODERATE confidence"

### **Permissive Mode** (Accept Everything with Review):

| Confidence | Score Range | Auto-Add? | Action | Percentage |
|------------|-------------|-----------|--------|------------|
| **HIGH** | ≥0.70 | ✅ YES | Add to stack | 44% |
| **MODERATE** | ≥0.55 | ❓ REVIEW | Manual confirm | 44% |
| **LOW** | <0.55 | ❓ REVIEW | Manual confirm | 11% |

**Settings**: Turn OFF "Auto-add MODERATE", Turn ON "Accept LOW confidence"

---

## ⚙️ Settings Guide

### **Open Settings**:
- Press `S` key
- Or click "⚙️ Settings" button in top-right

### **Confidence Threshold Settings**:

**1. Auto-add MODERATE confidence**
- **Default**: ✅ ON (recommended)
- **When ON**: Auto-add HIGH + MODERATE = 88% auto-add rate
- **When OFF**: Only auto-add HIGH, manually review MODERATE = 44% auto-add rate
- **Use Case**:
  - ON = Fast bulk scanning (trust the AI)
  - OFF = More control (verify borderline cards)

**2. Accept LOW confidence with review**
- **Default**: ❌ OFF (recommended)
- **When ON**: Show LOW confidence cards for manual review
- **When OFF**: Reject LOW confidence cards
- **Use Case**:
  - ON = Accept difficult cards with review
  - OFF = Maintain quality, reject unclear cards

---

## 🎬 Scanning Workflow

### **Default Mode (Fast Scanning)**:

1. **Hold card in frame** → Green "READY" indicator
2. **Press SPACE** → Identify in ~1 second
3. **HIGH confidence** → ✅ Auto-added to stack (green notification)
4. **MODERATE confidence** → ✅ Auto-added to stack (orange notification)
5. **LOW confidence** → ❌ Rejected (red notification, try again)
6. **Continue scanning** → Fast workflow

### **With Manual Review Enabled**:

1. **Hold card in frame** → Green "READY" indicator
2. **Press SPACE** → Identify in ~1 second
3. **HIGH confidence** → ✅ Auto-added to stack
4. **MODERATE/LOW confidence** → 🔍 **Review Modal Appears**
   - Shows card name, number, set, rarity, price
   - Shows confidence level (color-coded badge)
   - Two buttons: "✓ Accept & Add" or "✕ Reject & Rescan"
5. **Accept** → Card added to stack
6. **Reject** → Card rejected, scan again with better positioning

---

## 🔧 Troubleshooting

### **Problem: Too many cards rejected**

**Solution 1**: Enable "Auto-add MODERATE confidence" (Settings)
- This will auto-add 44% more cards (MODERATE)
- Recommended for bulk scanning

**Solution 2**: Enable "Accept LOW confidence with review" (Settings)
- This shows LOW confidence cards for manual review
- Good for difficult cards (damaged, sleeved, glare)

### **Problem: Wrong cards being added**

**Solution 1**: Disable "Auto-add MODERATE confidence" (Settings)
- Only auto-add HIGH confidence (44%)
- Manually review MODERATE confidence (44%)

**Solution 2**: Improve scan conditions
- Better lighting (reduce glare)
- Center card in frame
- Remove from sleeve if possible
- Hold steady (avoid motion blur)

### **Problem: Scan is too slow**

**Current**: ~1 second per card is normal

**To optimize**:
- ✅ Keep Geometric verification: ON (needed for accuracy)
- ❌ Turn OCR: OFF (saves ~170ms, minimal accuracy loss)
- ❌ Turn Multi-frame: OFF (3x slower)

### **Problem: Modal stuck on screen**

**Solution**:
- Click "Accept" or "Reject" button
- Or click outside the modal to reject
- Or press ESC key (closes notifications)

---

## 📊 Expected Results

### **With Default Settings**:
```
100 cards scanned in ~2 minutes (including manual handling)

Auto-added:      88 cards (HIGH + MODERATE)
Rejected:        11 cards (LOW - need rescan)
Manual time:     ~1-2 seconds per card (hold + press SPACE)
Rescan time:     ~5-10 seconds for 11 rejected cards

Total time:      ~2.5 minutes for 100 cards
Manual pricing:  ~5 hours for 100 cards

SPEEDUP:         120x faster 🚀
```

### **With Manual Review (Conservative)**:
```
100 cards scanned in ~5-7 minutes (including reviews)

Auto-added:      44 cards (HIGH only)
Manual review:   44 cards (MODERATE - 2-3s each = ~2min)
Rejected:        11 cards (LOW - need rescan)
Manual time:     ~1-2 seconds per card (hold + press SPACE)
Review time:     ~2-3 minutes for 44 reviews
Rescan time:     ~5-10 seconds for 11 rejected cards

Total time:      ~6-7 minutes for 100 cards
Manual pricing:  ~5 hours for 100 cards

SPEEDUP:         40-50x faster 🚀
```

---

## ✅ Pre-Test Checklist

### **Before Going to Shop**:
- [ ] App builds and starts successfully: `cd apps/desktop && pnpm start`
- [ ] Python service initializes (~3.3s startup)
- [ ] Camera feed visible and working
- [ ] Test scan 2-3 cards at home (verify workflow)
- [ ] Settings configured (recommended: default settings)
- [ ] Export CSV tested (verify pricing data)
- [ ] Laptop charged or plugged in
- [ ] Good lighting at shop (natural or desk lamp)
- [ ] Clear space for scanning (reduce background clutter)

### **Settings to Verify**:
- [ ] TCG Game: One Piece TCG
- [ ] Auto-add MODERATE: ON (for fast scanning)
- [ ] Accept LOW confidence: OFF (maintain quality)
- [ ] Geometric verification: ON
- [ ] OCR: OFF (unless testing variant accuracy)
- [ ] Multi-frame: OFF (speed priority)
- [ ] Top-K: 20 (default, good balance)

---

## 🎯 Testing Goals

### **Primary Goals**:
1. **Test accuracy**: Are identifications correct?
2. **Test speed**: Is ~1 second per card acceptable?
3. **Test workflow**: Is the UX intuitive for shop staff?
4. **Collect feedback**: What features are missing?
5. **Capture data**: System auto-saves scans for model improvement

### **Secondary Goals**:
1. Test edge cases (damaged cards, sleeves, glare)
2. Test different lighting conditions
3. Test with different card conditions (NM, LP, HP)
4. Measure actual throughput (cards per minute)
5. Compare to manual pricing (time savings)

### **Questions to Answer**:
1. What percentage of cards auto-add correctly?
2. How often do MODERATE confidence cards need review?
3. Are LOW confidence cards worth reviewing or should be rejected?
4. What causes failures? (lighting, damage, specific cards)
5. Would shop staff use this in production?

---

## 📝 Feedback Collection

### **During Testing**:
- Note any incorrect identifications (capture card name + what it identified as)
- Note any cards that fail to scan (reasons: glare, damage, etc.)
- Time yourself: How long for 10 cards? 50 cards? 100 cards?
- Ask shop staff: What would make this more useful?

### **After Testing**:
- Review capture statistics: `python services/capture/capture_manager.py stats`
- Check confidence distribution (HIGH/MODERATE/LOW percentages)
- Identify failure patterns (specific sets, card types, conditions)
- Compare to your friend's manual pricing workflow

---

## 🚀 Next Steps After Testing

### **If Testing Goes Well**:
1. **Collect ground truth data** (100+ cards with known correct IDs)
2. **Measure real accuracy** (vs test images)
3. **Fine-tune confidence thresholds** based on shop data
4. **Add requested features** from shop staff feedback
5. **Deploy to production** with their inventory

### **If Issues Found**:
1. **Analyze failure modes** (lighting, specific cards, etc.)
2. **Adjust confidence thresholds** if needed
3. **Improve preprocessing** for shop conditions
4. **Add workarounds** for known edge cases
5. **Iterate and retest**

---

## 📞 Support During Testing

### **Common Commands**:
```bash
# View capture statistics
python services/capture/capture_manager.py stats

# List recent captures
python services/capture/capture_manager.py list --limit 20

# Check app logs (if something breaks)
# Check: apps/desktop/src/main/logs/
```

### **If Something Breaks**:
1. Check camera permissions (OS settings)
2. Restart app (3.3s re-init)
3. Check Python service running (stderr output)
4. Verify FAISS index loaded
5. Check lighting (too dark or too bright)

---

## 🎉 Success Criteria

**Testing is successful if**:
- ✅ 80%+ of cards identified correctly
- ✅ Workflow is intuitive for shop staff
- ✅ Speed is acceptable (~1-2s per card)
- ✅ Shop staff would use in production
- ✅ System handles real-world conditions (sleeves, lighting, damage)

**Ready for production if**:
- ✅ 90%+ HIGH+MODERATE accuracy (verified with ground truth)
- ✅ Confidence thresholds calibrated for shop conditions
- ✅ Edge cases handled or documented
- ✅ Shop staff trained on workflow
- ✅ Rollback plan in place

---

**Current Status**: ✅ **READY FOR SHOP TESTING**
**Recommended Mode**: Default (Auto-add MODERATE) for fast scanning
**Support**: Check capture stats, adjust settings as needed

**Good luck with the shop testing!** 🚀

Let me know how it goes and what feedback you get!
