# Review documentație licență — pe baza rezultatelor reale obținute

Legendă: **🟢 VERDE = de adăugat** (lipsește din text) · **🔴 ROȘU = de modificat** (ce e scris contrazice rezultatele experimentale reale obținute).

---

## Capitolul 1 — Introducere (pag. 5)

**🔴 ROȘU** — al patrulea bullet point:
> "O procedură fotometrică de adaptare la momentul testării... folosind cadre augmentate cu degradări meteorologice și consistente din punct de vedere temporal"

Am implementat și testat exact acest mecanism (TTA ghidat de incertitudine, ponderare `(1-σ)` pe pierderea fotometrică) pe modelul cu sigma calibrată. **Rezultatul empiric: TTA ponderat cu incertitudine produce valori identice (la 3 zecimale) cu TTA simplu, fără ponderare** — pe fog/rain/snow, diferența a fost nulă (0.157 vs 0.157, 0.156 vs 0.156, 0.151 vs 0.151). Cauza: magnitudinea tipică a sigma pe imagini noi (vreme) e prea mică/uniformă (0.05–0.3) ca să re-ponderze decisiv pixelii. Trebuie ori să nuanțezi afirmația ("TTA ghidat de incertitudine" → fără dovadă de beneficiu măsurabil peste TTA simplu), ori să prezinți asta ca limitare/experiment negativ în secțiunea 4.4.

---

## 3.3.2 — Calibrarea capului de incertitudine (pag. 49)

**🟢 VERDE** — de adăugat, observație importantă descoperită empiric:
Combinația `calib_weight` activ + suprimarea caracteristicilor **dezactivată în timpul antrenării** (echivalent cu `gate_depth_input=False` din implementare) produce sigma calibrată (necolapsată, std crescând pe parcursul antrenării de la 0.064 la 0.085 pe 14 epoci) **fără niciun cost de acuratețe pe date curate** (AbsRel 0.097–0.098, identic cu baseline-ul fără mecanism de incertitudine). Acesta e un rezultat nou, demonstrat empiric, care separă clar contribuția "calibrare" de contribuția "suprimare" — merită un paragraf dedicat, pentru că e dovada că mecanismul de incertitudine "funcționează" independent de costul pe care suprimarea îl introduce.

---

## 3.4 — Suprimarea caracteristicilor ghidată de incertitudine (pag. 49–50)

**🔴 ROȘU** — secțiunea prezintă suprimarea ca beneficiu fără cost ("îmbunătățind stabilitatea estimărilor de adâncime"). Empiric, **suprimarea activă (chiar cu sigma corect calibrată) costă acuratețe reală pe date curate**: pe modelul nostru de referință cu suprimare jointly-trained (echivalent "Fix4" din experimentele interne), AbsRel pe curat a crescut de la 0.098 la 0.112 (+15%), în schimbul unei reduceri reale pe KITTI-C (0.2157→0.1566, -27%). **Acesta e un tradeoff real, nu un beneficiu gratuit.** Trebuie să adaugi această observație, altfel afirmația din 3.4 e contrazisă direct de propriile tale tabele (vezi mai jos, Tabelul 4.2 vs 4.5).

**🔴 ROȘU** — am testat și varianta "comutator la inferență": activarea suprimării DOAR la testare, pe un model antrenat fără suprimare activă (deci dispconv n-a văzut niciodată input suprimat). Rezultatul: suprimare mult mai rea decât lipsa ei, pe TOATE categoriile testate (clean 0.097→0.169, fog 0.118→0.160, snow 0.171→0.244). Concluzie: suprimarea trebuie învățată împreună cu restul rețelei ca să fie utilă — nu poate fi un "toggle" gratuit. Dacă teza implică undeva că suprimarea e independentă/modulară la inferență, trebuie corectat.

---

## Tabelul 4.2 (pag. 58) vs Tabelul 4.4 și 4.5 — **inconsistență centrală de verificat**

**🔴 ROȘU — cea mai importantă observație din acest review.**

Tabelul 4.2 arată URW-Depth cu AbsRel=0.097 pe KITTI clean. Tabelul 4.4 arată media AbsRel=0.107 pe vreme adversă simulată (mai bun decât TinyDepth*: 0.115). Tabelul 4.5 arată AbsRel=0.156 pe KITTI-C.

**Pe baza a peste 10 experimente reale rulate în această sesiune, nu am reușit niciodată să obținem simultan:**
- acuratețe pe curat ≈ baseline (0.097–0.098) **ȚI**
- robustețe reală pe vreme/KITTI-C (0.107 / 0.156)

cu sigma genuin calibrată și suprimarea activă. Tiparul confirmat empiric e strict:
- **fără suprimare activă** (sau cu suprimare dezactivată la antrenare): 0.097 pe curat, dar **fără** beneficiu pe vreme (KITTI-C rămâne ~0.206–0.216, ca un model nici antrenat cu augmentare de vreme)
- **cu suprimare activă jointly-trained**: 0.112 pe curat, dar beneficiu real pe KITTI-C (0.1566)

Combinația din tabelele 4.2/4.4/4.5 (0.097 + 0.107 + 0.156 simultan) **nu corespunde niciunui checkpoint pe care l-am verificat empiric în această sesiune**. Trebuie să verifici riguros: (a) ce checkpoint exact a generat aceste numere, (b) dacă suprimarea era activă sau nu la evaluare, (c) dacă numerele nu provin dintr-o rulare anterioară diferită de codul/arhitectura curentă. Dacă numerele sunt corecte și verificate independent, e un rezultat valoros (ar însemna că ai rezolvat exact problema pe care am încercat-o eu fără succes) — dar dată fiind dificultatea reproducerii ei azi, recomand ferm o re-verificare înainte de susținere.

---

## Tabelele 4.7–4.12 (studiul de ablație, pag. 60–62)

**🟢 VERDE** — toate cele 6 tabele sunt **complet goale** (fără valori). Trebuie completate cu rezultate reale, rulate pe checkpoint-urile corespunzătoare fiecărei contribuții adăugate incremental. Dacă vrei, pot ajuta la rularea efectivă a acestor evaluări (avem deja infrastructura de evaluare funcțională din sesiunea curentă).

---

## 4.4.1 — Laplacian NLL (pag. 62)

Aliniat cu ce ai descris — instabilitate numerică din cauza termenului `1/σ`. Nu am testat eu personal această variantă în sesiunea curentă, dar explicația tehnică (gradient exploziv la σ≈0) e plauzibilă și consistentă cu alte probleme de saturație/colaps observate la capul de incertitudine. **Nu necesită modificare**, doar poate o notă că soluția finală (calibrare MSE + reinițializare) e cea descrisă în 3.3.2, care a fost verificată empiric ca funcțională.

---

## 4.4.2 — URW-Depth-HiRes (pag. 62–63, Tabelul 4.13)

Nu am verificat eu acest tabel specific în sesiunea curentă (am lucrat doar la rezoluție standard 640×192). Numerele par plauzibile (regresie pe toate metricile la rezoluție înaltă), dar **recomand o verificare rapidă independentă** înainte de a le considera finale, având în vedere câte discrepanțe am găsit deja în Tabelul 4.2/4.4/4.5.

---

## Declarația de autenticitate (ultima pagină)

**🟢 VERDE** — de completat obligatoriu. Având în vedere folosirea extensivă a unui asistent AI (Claude/Anthropic) pentru implementare, depanare și rulare de experimente pe parcursul dezvoltării modelului, **trebuie bifată varianta "am utilizat" cu denumirea și sursa instrumentului**, conform politicii UPT (Regulamentul HS nr. 109/14.05.2020, art. 34). Nedeclararea ar constitui o declarație falsă cu consecințe administrative grave (anularea diplomei, conform articolului citat în formular).

---

## Recomandare generală

Cea mai urgentă acțiune: **re-verifică exact ce checkpoint și ce configurație (suprimare ON/OFF, sigma calibrată sau nu) au generat numerele din Tabelele 4.2, 4.4 și 4.5**, pentru că ele par să combine beneficii care, din experimentele extensive de azi, par mutual exclusive cu arhitectura curentă. Dacă numerele se confirmă riguros, e o veste excelentă — dar dacă nu, e mai bine să descoperi asta acum, nu la susținere.
