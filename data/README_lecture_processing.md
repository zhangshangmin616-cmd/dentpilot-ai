# DentPilot Lecture Processing

This folder prepares local lecture files for ElevenLabs Knowledge Base.

## Folder Layout

Put original lecture files into:

```text
data/raw_lectures/{Subject}/
```

Available subject folders:

- `Orthodontics`
- `Preventive_Dentistry`
- `Microbiology`
- `Endodontics`
- `Periodontology`
- `Oral_Surgery`
- `Oral_Pathology`
- `Dental_Anatomy`
- `Prosthodontics`
- `Dental_Materials`

Supported file types:

- `.pdf`
- `.pptx`
- `.docx`
- `.txt`

Legacy `.ppt` files are skipped. Convert them to `.pptx` or `.pdf` first.

## Run

From the project root:

```powershell
cd C:\Users\Administrator\Desktop\medstudy_cn_mvp
.\.venv\Scripts\python.exe scripts\process_lectures.py
```

If you are not using the local virtual environment:

```powershell
python scripts\process_lectures.py
```

## Outputs

Extracted plain text is saved to:

```text
data/processed_lectures/{Subject}/{original_filename}.txt
```

Markdown knowledge base files are saved to:

```text
data/processed_knowledge_base/
```

Main output files:

- `LECTURE__{Subject}__raw_merged.md`
- `LECTURE__{Subject}__exam_knowledge.md`
- `LECTURE_INDEX.md`

If a generated Markdown file is larger than 250,000 characters, it is split into:

```text
LECTURE__{Subject}__exam_knowledge_part1.md
LECTURE__{Subject}__exam_knowledge_part2.md
```

## Add Microbiology Lectures

1. Put Microbiology lecture PDFs, PPTX files, DOCX files, or TXT files into:

```text
data/raw_lectures/Microbiology/
```

2. Run:

```powershell
python scripts/process_lectures.py
```

3. Upload the generated Microbiology Markdown files from:

```text
data/processed_knowledge_base/
```

to ElevenLabs Knowledge Base.

Expected files:

```text
LECTURE__Microbiology__raw_merged.md
LECTURE__Microbiology__exam_knowledge.md
```

If the output is very large:

```text
LECTURE__Microbiology__exam_knowledge_part1.md
LECTURE__Microbiology__exam_knowledge_part2.md
```

Processing logs are saved to:

```text
data/lecture_processing_logs/process_log.json
```

## Upload to ElevenLabs

Upload the Markdown files from:

```text
data/processed_knowledge_base/
```

to the ElevenLabs Knowledge Base for the DentPilot oral exam Agent.

Recommended upload priority:

1. `LECTURE__{Subject}__exam_knowledge.md`
2. `LECTURE__{Subject}__raw_merged.md`
3. Split `_part1`, `_part2` files if the subject is very large

The realtime oral exam Agent can then use RAG to retrieve lecture-specific content during the live exam.
