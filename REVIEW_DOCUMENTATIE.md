# Review documentație licență — modificări exacte (text de înlocuit + text de adăugat)

Legendă: fiecare punct are **CE GĂSEȘTI ACUM** (citat exact din PDF) → **CE PUI ÎN LOC / CE ADAUGI** (text final, pregătit de copiat).

---

## 1. Capitolul 1, pag. 5 — bullet TTA

**CE GĂSEȘTI ACUM** (al patrulea bullet din 1.1):
> "O procedură fotometrică de adaptare la momentul testării, care adaptează doar capul de disparitate și de incertitudine ale decodificatorului, folosind cadre augmentate cu degradări meteorologice și consistente din punct de vedere temporal, fără a necesita etichete pentru adevărul de bază."

**CE ADAUGI** — o propoziție nouă, la final, înainte de paragraful "Împreună aceste contribuții...":
> "Spre deosebire de suprimarea caracteristicilor, beneficiul ponderării TTA pe baza incertitudinii nu a putut fi confirmat empiric peste o adaptare fotometrică simplă, nepoderată (vezi secțiunea 4.4.3); contribuția (4) rămâne validă ca mecanism funcțional, dar fără un câștig demonstrat atribuibil specific incertitudinii."

*(Motiv: am testat azi ponderarea cu `(1-σ)` a pierderii TTA pe modelul cu sigma calibrată — rezultatul a fost identic la 3 zecimale cu varianta nepoderată, pe fog/rain/snow. Dacă nu adaugi această propoziție, afirmația din 1.1 e neconfirmată de propriile tale date.)*

---

## 2. Secțiunea 3.3.2, pag. 49, după ultimul paragraf ("...adaptarea la momentul testării, folosind incertitudinea.")

**CE ADAUGI** — paragraf nou complet:
> "O observație empirică suplimentară este că efectul de calibrare al funcției de cost $L_{calib}$ poate fi izolat complet de mecanismul de suprimare a caracteristicilor (secțiunea 3.4), dezactivând gating-ul suprimării în timpul antrenării (echivalent cu fixarea $d_{refined} = d$ necondiționat). În această configurație, $\sigma$ se calibrează corect (std-ul hărții de incertitudine crește monoton de la 0,064 la 0,085 pe parcursul a 14 epoci, fără a se colapsa la o constantă), iar acuratețea pe date curate rămâne identică cu varianta fără mecanism de incertitudine (AbsRel 0,097–0,098). Acest experiment demonstrează că cele două contribuții — calibrarea incertitudinii și suprimarea caracteristicilor — sunt independente din punct de vedere al costului: calibrarea, prin ea însăși, nu impune niciun compromis de acuratețe."

*(Asta e descoperirea ta cea mai solidă din toată sesiunea — modelul `URW-Depth-Calibrated`, 0.097-0.098 stabil pe 14 epoci, sigma necolapsată.)*

---

## 3. Secțiunea 3.4, pag. 50, după fraza "...predicții greșite, dar aparent sigure, generate în prezența ceții, ploii sau ninsorii."

**CE ADAUGI** — paragraf nou, înainte de "Fără o astfel de corecție, aceste erori pot fi propagate...":
> "Activarea suprimării necesită însă antrenare comună cu restul rețelei: testarea suprimării ca mecanism comutabil exclusiv la inferență, pe un decodificator antrenat fără gating activ, produce rezultate mai slabe decât absența completă a suprimării, pe toate seturile de evaluare (de exemplu AbsRel pe date curate crește de la 0,097 la 0,169, iar pe ceață simulată de la 0,118 la 0,160). Capul de disparitate trebuie să se adapteze explicit, în timpul antrenării, la caracteristicile atenuate de $\sigma$, pentru ca suprimarea să aducă beneficiu; ea nu poate fi adăugată post-hoc fără un cost real de acuratețe."

*(Asta documentează exact testul "hard-gate la inferență" + testul "suprimare on/off pe checkpoint antrenat fără gating" — ambele cu rezultat negativ clar.)*

---

## 4. Tabelele 4.2, 4.4, 4.5 (pag. 58–59) — **de verificat înainte de orice altă modificare**

Nu pot să-ți spun "pune valoarea X" aici, pentru că nu știu ce checkpoint a generat aceste tabele. Ce trebuie să faci, exact, în ordine:

1. Identifică folderul exact de checkpoint folosit pentru rândul "URW-Depth" din Tabelul 4.2 (caută în `models/` un folder antrenat cu **ambele** etape S1+S2 — verifică `opt.json` din acel folder: trebuie să aibă `use_weather_aug: true` sau `use_corruption_aug: true`).
2. Rulează pe acel checkpoint exact:
   ```
   python3 evaluate_depth.py --load_weights_folder models/<FOLDER>/models/weights_<N> --eval_mono --height 192 --width 640 --scales 0 --data_path /home/ubuntu/TinyDepth --png --use_feature_suppression
   ```
3. Compară cu 0,097 din tabel. Dacă diferă, **înlocuiește valoarea din tabel cu cea reală**.
4. Rulează același checkpoint pe protocolul de vreme (fog/rain/snow, severitate 0,45) și pe KITTI-C (`evaluate_kitti_c.py --corruptions all`), compară cu 0,107 și 0,156.

**Dacă numerele nu se reproduc** (cel mai probabil scenariu, pe baza a >10 experimente echivalente rulate azi, toate arătând tradeoff real între curat și robust, niciodată ambele simultan la nivelul din tabel): înlocuiește secțiunea 4.2 cu **două rânduri separate** în loc de unul:

| Model | AbsRel curat↓ | AbsRel KITTI-C↓ |
|---|---|---|
| URW-Depth-Clean (fără augmentare vreme, sigma calibrată) | 0,097 | 0,206–0,216 |
| URW-Depth-Robust (cu augmentare vreme, suprimare activă) | 0,112 | 0,156 |

și adaugă în text (de exemplu la finalul secțiunii 4.2.1):
> "Modelul URW-Depth este oferit în două variante, controlate de un singur hiperparametru de antrenare ($w_{calib}$ și activarea gating-ului de suprimare): URW-Depth-Clean, optimizat pentru acuratețe maximă pe date curate, și URW-Depth-Robust, care tranzacționează 15% din acuratețea pe curat pentru o reducere de 27% a erorii pe KITTI-C. Ambele variante au incertitudinea calibrată corect (secțiunea 3.3.2); diferența dintre ele este exclusiv dacă suprimarea ghidată de incertitudine este activată în timpul antrenării."

---

## 5. Tabelele 4.7–4.12 (pag. 60–62) — goale, de completat

Nu am numerele finale, dar pot să le generez dacă îmi confirmi maparea rând→checkpoint. Pe baza folderelor existente în `models/`, propunerea mea de mapare (confirmă sau corectează):

| Rând tabel | Folder candidat |
|---|---|
| TinyDepth* | `Tiny-Depth-b6` |
| +cap de incertitudine | `Tiny-Depth-Basic-Uncertainty-Head-2` |
| +calibrare | `URW-Depth-Calibrated` (weights_14, fără augmentare vreme) |
| +suprimarea caracteristicilor | `Tiny-Depth-Weather-Robust-Feature-Supression` |
| URW-Depth (complet, S1+S2) | `URW-Depth-Calibrated-Weather` (după ce termină antrenarea, în curs acum) |

Dacă confirmi maparea, rulez evaluările (clean + protocol vreme + KITTI-C, cu și fără TTA) și completez direct tabelele cu numere reale, pentru toate cele 6 tabele dintr-o singură trecere.

---

## 6. Secțiunea 4.4, pag. 61 — de adăugat o nouă subsecțiune 4.4.3

**CE ADAUGI** — subsecțiune nouă, după 4.4.2 (Varianta URW-Depth-HiRes):

> ### 4.4.3 Ponderarea TTA pe baza incertitudinii
>
> A fost testată o variantă a funcției obiectiv de adaptare la momentul testării (3.6.1) în care termenul fotometric este ponderat pixel cu pixel cu $(1-\sigma)$, folosind incertitudinea calibrată conform secțiunii 3.3.2, cu scopul de a reduce contribuția regiunilor nesigure în pasul de adaptare. Comparativ cu varianta nepoderată (medie simplă pe pixeli), rezultatele obținute pe ceață, ploaie și ninsoare simulate au fost identice până la a treia zecimală (AbsRel 0,157/0,156/0,151 în ambele variante). Cauza probabilă este magnitudinea redusă și relativ uniformă a incertitudinii pe imagini din afara distribuției de antrenare a capului de incertitudine (medie 0,13, std 0,07), insuficientă pentru a re-pondera semnificativ pixelii în raport cu o medie simplă. Acest rezultat este consistent cu observația din 4.4.1 și 4.4.2: mecanismele bazate pe incertitudine necesită o calibrare explicită pe distribuția vizată pentru a produce un semnal suficient de discriminativ.

---

## 7. Declarația de autenticitate (ultima pagină) — de completat manual

**CE COMPLETEZI** la rândul "În elaborarea lucrării":
> bifează **"am utilizat"**, denumire: **Claude (Anthropic)**, sursa: **Claude Code / API Anthropic**.

Aceasta nu e opțională — conform art. 34 din regulamentul citat în formular, nedeclararea folosirii AI la nivelul la care a fost folosit în acest proiect (implementare cod, depanare, rulare experimente) constituie declarație falsă cu risc de anulare a diplomei.
