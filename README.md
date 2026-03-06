# Come ho fatto girare Qwen-Image-Layered (57GB) su PC locale — guida completa

**Qwen-Image-Layered** è un modello di Alibaba/Qwen capace di decomporre qualsiasi immagine in layer RGBA separati, esattamente come farebbe un artista in Photoshop — ma in modo completamente automatico. Il risultato è esportabile in PNG, ZIP, PPTX e PSD.

Per chi lavora in VFX, motion graphics o post-produzione, le implicazioni sono immediate: separazione automatica di elementi, maschere alpha pronte all'uso, layer indipendenti su cui fare editing.

Questa è la guida completa per farlo girare su un PC Windows con GPU NVIDIA — tutto locale, zero cloud, zero costi di API.

---

## Hardware utilizzato

- **GPU:** NVIDIA GeForce RTX 3090 (24GB VRAM)
- **CPU:** AMD Ryzen Threadripper 3970X
- **RAM:** 256GB
- **OS:** Windows 11
- **Storage:** disco D: dedicato (il modello pesa ~57GB)

La RAM abbondante è fondamentale — il modello non entra interamente in 24GB di VRAM, quindi parte dei layer viene gestita in RAM tramite `device_map="balanced"`.

---

## Prerequisiti

- Python 3.10 installato
- Git installato (con Git LFS)
- Driver NVIDIA aggiornati (CUDA 12.x)
- ~80GB liberi su disco (57GB modello + spazio per venv e repo)

---

## FASE 1 — Struttura cartelle

Apri **cmd come amministratore** e crea la struttura sul disco D:

```cmd
mkdir D:\AI\Qwen-Image-Layered
mkdir D:\AI\Qwen-Image-Layered\model
mkdir D:\AI\Qwen-Image-Layered\output
```

---

## FASE 2 — Virtual Environment Python

Creare un venv è essenziale per isolare le dipendenze e rendere il progetto portabile.

```cmd
cd D:\AI\Qwen-Image-Layered
python -m venv venv
venv\Scripts\activate
```

**Regola d'oro:** ogni volta che apri un nuovo cmd, prima di qualsiasi operazione:
```cmd
cd D:\AI\Qwen-Image-Layered
venv\Scripts\activate
```
Il prompt deve mostrare `(venv)` all'inizio. Puoi verificare con `where python` — deve rispondere con il path dentro `D:\AI\Qwen-Image-Layered\venv\`.

---

## FASE 3 — Installazione dipendenze

**PyTorch con CUDA 12.1** (il build stabile più recente compatibile con driver 591.x):

```cmd
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

Circa 2.5GB di download. Poi le librerie del progetto:

```cmd
pip install git+https://github.com/huggingface/diffusers.git
pip install transformers accelerate huggingface_hub sentencepiece protobuf
pip install gradio python-pptx psd-tools
```

---

## FASE 4 — Download del modello (57GB)

Il metodo più affidabile su Windows è **git lfs**, che gestisce correttamente il resume in caso di interruzione:

```cmd
git lfs install
git clone https://huggingface.co/Qwen/Qwen-Image-Layered D:\AI\Qwen-Image-Layered\model
```

Il download richiede tempo — dipende dalla connessione. Se si interrompe:
```cmd
cd D:\AI\Qwen-Image-Layered\model
git lfs pull
```

> **Nota:** il metodo `snapshot_download` di huggingface_hub non gestisce bene il resume su Windows con il nuovo sistema xet — ogni interruzione riparte quasi da zero. `git lfs` è molto più robusto.

---

## FASE 5 — Clone del repo con la UI Gradio

Il team Qwen ha pubblicato il codice della demo su GitHub, inclusa una UI Gradio completa:

```cmd
cd D:\AI\Qwen-Image-Layered
git clone https://github.com/QwenLM/Qwen-Image-Layered.git repo
```

---

## FASE 6 — Verifica installazione

Prima di lanciare, verifica che tutto sia a posto:

```python
# check.py
import os

model_dir = r"D:\AI\Qwen-Image-Layered\model"
total = 0
files = 0
for root, dirs, filenames in os.walk(model_dir):
    for f in filenames:
        fp = os.path.join(root, f)
        total += os.path.getsize(fp)
        files += 1
print(f"File trovati: {files}")
print(f"Dimensione totale: {total / 1024**3:.2f} GB")

import torch
print(f"CUDA disponibile: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
```

```cmd
python check.py
```

Output atteso: ~57GB, `CUDA disponibile: True`, nome GPU corretto.

---

## FASE 7 — Configurazione app.py

Il file originale `repo/src/app.py` carica il modello da HuggingFace online. Dobbiamo modificarlo per usare il modello locale e risolvere il problema VRAM.

Le modifiche chiave sono tre:

**1. Path del modello — locale invece di HuggingFace:**
```python
MODEL_PATH = r"D:\AI\Qwen-Image-Layered\model"
ASSETS_PATH = r"D:\AI\Qwen-Image-Layered\repo\assets\test_images"
```

**2. Caricamento con device_map="balanced":**
```python
pipeline = QwenImageLayeredPipeline.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.bfloat16,
    device_map="balanced"
)
```

Perché `device_map="balanced"` e non `.to("cuda")`? Il modello in bfloat16 occupa ~28-29GB — leggermente sopra i 24GB della 3090. Con `balanced`, Diffusers distribuisce automaticamente i layer tra VRAM e RAM, ottimizzando il throughput senza andare in OOM.

**3. Path degli esempi — assoluto:**
```python
examples = [os.path.join(ASSETS_PATH, f"{i}.png") for i in range(1, 14)]
```

**4. Accesso da LAN** — già configurato nell'originale:
```python
demo.launch(server_name="0.0.0.0", server_port=7869)
```

Apri la porta nel firewall Windows:
```cmd
netsh advfirewall firewall add rule name="Qwen-Image-Layered" dir=in action=allow protocol=TCP localport=7869
```

---

## FASE 8 — Script di lancio

Crea `AVVIA.bat` nella root del progetto:

```bat
@echo off
title Qwen-Image-Layered
cd /d D:\AI\Qwen-Image-Layered
call venv\Scripts\activate
echo.
echo  Qwen-Image-Layered avviato!
echo  Apri il browser su: http://localhost:7869
echo.
python repo\src\app.py
pause
```

Doppio click su `AVVIA.bat` — il modello si carica in ~10 secondi e l'interfaccia è disponibile su `http://localhost:7869` (o `http://[IP_PC]:7869` dalla LAN).

---

## Problemi incontrati e soluzioni

### Download interrotto che riparte da zero
`snapshot_download` con il nuovo sistema xet di HuggingFace non gestisce bene il resume su Windows. Soluzione: usare `git lfs clone` che è nativamente riprendibile.

### VRAM insufficiente (OOM o tempi enormi)
Con ComfyUI o altri processi attivi, la VRAM era quasi satura (24/24GB). Risultato: 354 secondi per step invece di 21. Soluzione: chiudere tutti i processi GPU prima di lanciare, e usare `device_map="balanced"` invece di `.to("cuda")`.

### `enable_model_cpu_offload()` più lento del previsto
Il cpu offload creava un conflitto di device (`input_ids` su CUDA, modello su CPU) che rallentava tutto. `device_map="balanced"` è più intelligente perché distribuisce staticamente i layer prima dell'inferenza invece di spostarli dinamicamente.

### `huggingface-cli` non trovato nel venv
Il CLI non viene aggiunto al PATH automaticamente. Soluzione: `python -m huggingface_hub.commands.huggingface_cli` oppure usare direttamente `snapshot_download` via Python.

---

## Tempi di inferenza realistici

Con RTX 3090 24GB + 256GB RAM, `device_map="balanced"`, ComfyUI chiuso:

| Steps | Layer | Tempo stimato |
|-------|-------|---------------|
| 20    | 2     | ~7 minuti     |
| 50    | 2     | ~17 minuti    |
| 20    | 4     | ~14 minuti    |
| 50    | 4     | ~35 minuti    |

Non è real-time, ma per uso professionale in pipeline VFX è accettabile — soprattutto considerando che sostituisce ore di rotoscoping manuale.

---

## Output disponibili

Ogni generazione produce automaticamente:
- **Gallery PNG** — ogni layer come immagine RGBA separata
- **ZIP** — tutti i layer in un archivio
- **PPTX** — layer sovrapposti su una slide PowerPoint (utile per presentazioni)
- **PSD** — file Photoshop con layer separati pronti per l'editing

---

## Considerazioni finali

Qwen-Image-Layered è uno strumento concreto per chi lavora con immagini in modo professionale. La decomposizione automatica in layer RGBA apre possibilità interessanti in VFX, compositing, e asset generation per motion graphics.

Il setup non è banale — 57GB di modello, gestione VRAM, configurazione Windows — ma una volta in piedi gira in modo stabile e accessibile da qualsiasi dispositivo in LAN tramite browser.

Il codice completo e i file di configurazione sono disponibili su:
- Modello: https://huggingface.co/Qwen/Qwen-Image-Layered
- Repo: https://github.com/QwenLM/Qwen-Image-Layered

---

*Testato su Windows 11, Python 3.10, PyTorch 2.5.1+cu121, Diffusers 0.37.0.dev, RTX 3090 24GB*
