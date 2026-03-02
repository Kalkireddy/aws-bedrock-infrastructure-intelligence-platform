# How to Import Architecture Diagrams into diagrams.net

Your SRE Automation architecture diagram is ready in **multiple formats** for easy import into diagrams.net. Choose the method that works best for you:

---

## Method 1: Import JSON File (RECOMMENDED)

**Step-by-Step:**

1. **Go to diagrams.net** → https://app.diagrams.net
2. **Click File** → **Open** (or press `Ctrl+O` / `Cmd+O`)
3. **Select the JSON file:**
   ```
   docs/ARCHITECTURE_DIAGRAM_SIMPLE.json
   ```
4. **Click Open** → Diagram loads automatically
5. **Save to your account** (optional) → File → Save As

**Result:** Full interactive architecture diagram with all AWS components, connections, and styling.

---

## Method 2: Copy-Paste XML (Alternative)

If JSON method doesn't work:

1. **Open** `docs/DIAGRAMS_NET_EXPORT.xml` in your editor
2. **Copy ALL content** (Ctrl+A → Ctrl+C)
3. **Go to diagrams.net** → File → New
4. **Paste:** Ctrl+V
5. **Select "Replace current diagram"** when prompted
6. **Click OK**

**Result:** Same diagram, loaded from XML format.

---

## Method 3: Manual Recreation (Quick, 5 minutes)

If automated import doesn't work, recreate using our visual guide:

### **Layer 1: Compute (Orange boxes)**
```
EC2 Instance (t3.micro)
├─ SRE Agent Lambda
├─ Maintenance Lambda
└─ AI Chatbot Lambda
```

### **Layer 2: Monitoring (Green/Purple boxes)**
```
CloudWatch (metrics, logs, alarms, dashboard)
├─ Alarms (CPU > 75%, Disk > 80%)
└─ EventBridge (2 AM UTC scheduled rule)
```

### **Layer 3: Storage (Blue boxes)**
```
S3 Bucket (sre-automation-logs)
└─ DynamoDB (3 tables: resize-requests, approvals, cache)
```

### **Layer 4: External (Red/Purple boxes)**
```
SNS Topic → Email Alerts → Your Team
Amazon Bedrock (Nova Pro AI model)
```

### **Connections:**
- EC2 → CloudWatch (metrics flow)
- CloudWatch → SRE Agent (trigger analysis)
- SRE Agent → DynamoDB & SNS (store & notify)
- EventBridge → Maintenance Lambda (scheduled trigger)
- CloudWatch → S3 (log archival)
- S3 → AI Chatbot (fetch logs)
- AI Chatbot → Bedrock & DynamoDB (analyze & cache)
- SNS → Team (email notifications)

---

## File Locations in Your Project

```
FREELANCE/repo-root/docs/
├── ARCHITECTURE_DIAGRAM_SIMPLE.json      ← 🔥 Try this first
├── DIAGRAMS_NET_EXPORT.xml               ← Backup XML option
├── ARCHITECTURE_DIAGRAMS.md              ← Markdown with Mermaid diagrams
├── CLIENT_HANDOVER_GUIDE.md              ← Full presentation guide
└── QUICK_REFERENCE_CARD.md               ← Operations reference
```

---

## Troubleshooting

### Problem: "File format not supported"
**Solution:** Try Method 2 (XML copy-paste) or Method 3 (manual recreation)

### Problem: "Diagram loads but no colors/styling"
**Solution:** 
1. Refresh the page (F5)
2. Try file → Open from computer again
3. Use Method 2 XML import as backup

### Problem: "Can't find the file"
**Solution:** 
1. Make sure you're in the right directory:
   ```bash
   ls -la /Volumes/DevOps-SSD/Projects/FREELANCE/repo-root/docs/
   ```
2. Check filename spelling exactly

### Problem: Still having issues?
**Quick Fix:** Copy the diagram description below into diagrams.net manually in 10 minutes.

---

## Visual Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                  AWS Account (995429641089)                     │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ EC2 Instance │→ │ SRE Agent    │→ │ DynamoDB     │          │
│  │ t3.micro     │  │ Lambda       │  │ (requests)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│        ↓                                      ↓                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ CloudWatch   │→ │ S3 Bucket    │→ │ AI Chatbot   │→→→ SNS  │
│  │ (metrics)    │  │ (logs)       │  │ Lambda       │   (📧)  │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│        ↓                                      ↓                  │
│  ┌──────────────┐                     ┌──────────────┐          │
│  │ EventBridge  │──→ │Maintenance│    │ Bedrock      │          │
│  │ (2 AM UTC)   │    │ Lambda    │    │ (Nova Pro)   │          │
│  └──────────────┘    └──────────┘     └──────────────┘          │
│                                             ↓                   │
│                                      ┌──────────────┐            │
│                                      │ Your Team 👥 │            │
│                                      │ Notifications│            │
│                                      └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Next Steps

✅ **Once diagram is imported:**
1. Save it in your diagrams.net account
2. Share link with your team
3. Update styling/positioning as needed
4. Export as PNG/PDF for presentations

✅ **Integration with diagrams.net:**
- Real-time collaboration (team editing)
- Version history tracking
- Export to multiple formats (PNG, PDF, SVG)
- Embed in documents/websites

---

## Need Help?

Check our comprehensive guides:
- **CLIENT_HANDOVER_GUIDE.md** - Full architecture explanation
- **ARCHITECTURE_DIAGRAMS.md** - Mermaid diagrams + flowcharts
- **QUICK_REFERENCE_CARD.md** - Quick operational reference

All in: `/Volumes/DevOps-SSD/Projects/FREELANCE/repo-root/docs/`
