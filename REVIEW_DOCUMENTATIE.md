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
| URW-Depth (S2 #1: calibrare, fără vreme, fără suprimare) | 0,097–0,098 | 0,206–0,216 |
| URW-Depth-Weather (S2 #2, continuă de la URW-Depth: + vreme + suprimare reală) | *(antrenare nouă în curs — vechea rulare avea suprimarea inertă, vezi nota de mai jos)* | de verificat |

și adaugă în text (de exemplu la finalul secțiunii 4.2.1):
> "Modelul URW-Depth este obținut prin prima rulare a protocolului S2 (secțiunea 3.7), pornind de la punctul de control rezultat din S1, cu augmentările de vreme și suprimarea caracteristicilor dezactivate — izolând efectul pur al calibrării incertitudinii (secțiunea 3.3.2). Modelul URW-Depth-Weather continuă fine-tuning-ul de la URW-Depth printr-o a doua rulare S2, în care se activează atât augmentările de vreme cât și suprimarea caracteristicilor ghidată de incertitudinea deja calibrată. Costul de acuratețe pe date curate observat pentru URW-Depth-Weather reflectă acum contribuția combinată a antrenării pe distribuție augmentată ȚI a suprimării active ghidate de incertitudine."

**🔴 Important — istoric de corecție, relevant pentru verificare finală**: o primă variantă a lui URW-Depth-Weather a fost antrenată cu `no_suppression_gating` activ din eroare, ceea ce făcea suprimarea inertă la inferență (capul de detecție a corupției `g` nefiind supravegheat, rămânea ≈0, anulând efectul suprimării indiferent de valoarea sigma). Modelul a fost reantrenat corect (fără acel flag, suprimare genuin activă) — **înainte de a finaliza tabelele cu numerele din această secțiune, confirmă că checkpoint-ul folosit e cel din rularea corectă** (verifică `opt.json`: `no_suppression_gating` trebuie să fie `false` sau absent pentru URW-Depth-Weather).

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

> ### 4.4.3 Capul global de detecție a corupției și gating-ul suprimării ghidat de un al doilea semnal
>
> Motivația acestui experiment a fost rezolvarea tensiunii structurale dintre acuratețea pe date curate și robustețea la vreme adversă (secțiunea 4.2): suprimarea caracteristicilor (secțiunea 3.4), fiind un mecanism substractiv, costă acuratețe pe orice imagine pe care este aplicată, indiferent dacă imaginea este sau nu efectiv corupta. Ideea testată a fost introducerea unui al doilea cap, separat de capul de incertitudine, care să prezică explicit probabilitatea ca o imagine să fie corupta ($g \in [0,1]$, supravegheat cu eticheta reală din pipeline-ul de augmentare), folosit pentru a gata suprimarea: $d_{refined} = d \cdot (1 - g \cdot \sigma)$, astfel încât suprimarea să rămână inactivă ($g \approx 0$) pe imagini curate și activă ($g \approx 1$) doar pe imagini corupte.
>
> O primă variantă a capului, citind doar media RGB globală a imaginii de intrare, nu a învățat nicio discriminare ($g \approx 0{,}5$ constant, indiferent de imagine), inclusiv după mărirea ponderii pierderii de 10 ori. Cauza root-cause identificată a fost faptul că degradările de tip neclaritate și zgomot (incluse alături de ceață/ploaie/zăpadă în eticheta de antrenare) nu modifică media RGB globală (verificat empiric: variația mediei este de ordinul $10^{-2}$ pentru neclaritate, față de ordinul $10^1$ pentru ceață), introducând o etichetare contradictorie pentru un cap care citește doar acest semnal. Restrângerea etichetei doar la corupțiile cu semnătură globală de culoare (ceață/ploaie/zăpadă) și extinderea intrării capului cu deviația standard per canal (pentru a captura și reducerea de contrast) nu au rezolvat problema la rata de învățare standard a rețelei principale. Capul a învățat să discrimineze abia după alocarea unui grup de optimizare separat, cu o rată de învățare de 100 de ori mai mare (justificat de faptul că este un perceptron multistrat mic, antrenat de la zero, fără relație de partajare a gradientului cu restul rețelei).
>
> Capul re-calibrat astfel discriminează corect imaginile pe distribuția proprie de antrenare (diferență de peste 0,5 între probabilitatea medie pe imagini curate și pe imagini cu ceață simulată), însă **nu generalizează** la corupțiile reale din KITTI-C: pe tipurile de vreme reale (ceață, zăpadă, îngheț), gating-ul rezultat produce o acuratețe mai slabă decât absența completă a suprimării (de exemplu pe zăpadă, AbsRel crește de la 0,191, fără suprimare, la 0,341, cu gating activ) — cauza fiind un decalaj de distribuție între statisticile augmentărilor sintetice de antrenare și cele ale corupțiilor reale din KITTI-C. Extinderea setului de augmentări de antrenare cu trei tipuri calibrate explicit pe statisticile reale ale KITTI-C (contrast, luminozitate, îngheț — secțiunea 3.5.1) nu a redus acest decalaj, ci a degradat suplimentar performanța pe unele tipuri de corupție reale.
>
> Două variante adiționale, testate exclusiv la inferență, pe un cap deja antrenat, nu au adus beneficiu: forțarea gating-ului la valori binare (\textit{hard-gate}, $g \in \{0,1\}$) a produs rezultate mai slabe decât gating-ul continuu, din cauza varianței reziduale a lui $g$ pe imagini curate (medie 0,13, deviație standard 0,07), care, forțată la extrem, amplifică eroarea pe imaginile clasificate accidental ca fiind corupte; și ascuțirea graduală a gate-ului printr-un parametru de temperatură a produs o degradare monotonă pe fiecare temperatură testată, pe fiecare tip de corupție evaluat, fără nicio valoare intermediară superioară gate-ului neascuțit. În sfârșit, folosirea aceleiași incertitudini calibrate pentru a pondera funcția obiectiv de adaptare la momentul testării (3.6.1) cu factorul $(1-\sigma)$ nu a produs nicio diferență măsurabilă față de adaptarea nepoderată, din același motiv structural — magnitudinea incertitudinii pe imagini din afara distribuției proprii de calibrare este insuficient de discriminativă.
>
> Concluzia acestei serii de experimente este că un mecanism de gating bazat pe un cap supervizat separat poate fi calibrat să discrimineze corect pe propria distribuție de antrenare, dar nu generalizează suficient pentru a rezolva tensiunea structurală dintre acuratețe și robustețe descrisă în secțiunea 4.2, motiv pentru care soluția finală adoptată în URW-Depth/URW-Depth-Weather (secțiunea 3.7) renunță la acest cap suplimentar, în favoarea a două rulări separate ale protocolului S2.

*(Notă: am inclus aici și testul de ponderare TTA, ca parte a aceleiași serii de experimente negative legate de capul de gating — face parte din aceeași poveste, nu o subsecțiune separată.)*

---

## 7. Secțiunea 3.5.1, pag. 50 — augmentări meteorologice extinse de la 3 la 6 tipuri

**CE GĂSEȘTI ACUM** (primul paragraf din 3.5.1):
> "Cand augmentările meteorologice sunt active, fiecare imagine de la antrenare este independent și aleator perturbată cu una dintre cele trei efecte aplicate la severități aleatoare în intervalul [0,1]."

**CE PUI ÎN LOC:**
> "Când augmentările meteorologice sunt active, fiecare imagine de la antrenare este independent și aleator perturbată cu unul dintre șase efecte aplicate la severități aleatoare în intervalul [0,1]: trei corespunzând fenomenelor meteorologice propriu-zise (ceață, ploaie, ninsoare) și trei corespunzând unor degradări globale de culoare/contrast (contrast redus, luminozitate crescută, înghețare/"frost"), introduse pentru a alinia statistic distribuția de antrenare cu corupțiile reale din KITTI-C, ale căror semnături de medie și deviație standard per canal diferă semnificativ de cele produse de augmentările meteorologice simple (verificat empiric: shift de medie ~67 pentru ceața simulată inițial vs. magnitudini diferite pentru frost/contrast/brightness din KITTI-C real)."

**CE ADAUGI** — după paragrafele despre ceață/ploaie/ninsoare (înainte de "Aceste augmentări sunt aplicate aproape identic..."), trei paragrafe noi:

> "Pentru efectul de contrast redus se calculează media per canal a imaginii și se reduce abaterea fiecărui pixel față de această medie cu un factor proporțional cu severitatea ($severity \in [0.4, 0.85]$), păstrând media globală practic neschimbată, dar reducând deviația standard per canal — efect verificat empiric ca fiind reprezentativ pentru corupția "contrast" din KITTI-C (deviația standard scade de la aproximativ 84 la aproximativ 17 pe canal, media rămânând neschimbată).
>
> Pentru efectul de luminozitate crescută se aplică o combinație de scalare și deplasare aditivă către alb, cu severitate în $[0.3, 0.6]$, simulând o creștere a mediei per canal de 50–60 unități cu o reducere moderată a contrastului, reprezentativă pentru corupția "brightness" din KITTI-C.
>
> Pentru efectul de înghețare ("frost") se aplică un amestec aditiv cu o culoare alb-albăstruie (R=200, G=210, B=220), cu severitate în $[0.4, 0.8]$, producând o creștere mare a mediei per canal (aproximativ 80–90 unități), reprezentativă pentru corupția "frost" din KITTI-C."

*(Motiv: am verificat azi empiric, comparând imagini reale din `kitti_c/kitti_c/{fog,snow,frost,brightness,contrast}`, că augmentările meteorologice originale — fog/rain/snow — produc un profil statistic de medie/std diferit de corupțiile reale KITTI-C, ceea ce cauza o generalizare slabă a modelului antrenat doar pe ele. Cele trei funcții noi sunt calibrate direct pe statisticile reale măsurate.)*

---

## 8. Secțiunea 3.7, pag. 53 — etapa S2 este configurabilă și rulată de două ori

**CE GĂSEȘTI ACUM** (al treilea și al patrulea paragraf din 3.7, pag. 53 — de la "Etapa a doua (S2) este dedicată..." până la final):
> "Etapa a doua (S2) este dedicată adaptării la condiții meteorologice și vizuale dificile, și pornind de la rezultatele primei etape, modelul este antrenat pe setul de date KITTI augmentat cu degradări vizuale și de vreme, expunând rețeaua la condițiile de degradare față de care trebuie să fie robustă la momentul rulării pe dispozitive. Această etapă folosește o rată de învățare mai mică, pentru a adapta reprezentările pre-antrenate la distribuția de date augmentată fără a suprascrie ceea ce a fost învățat în S1. Această separare clarifică totodată atribuirea în experimentele din capitolul 4, unde variantele de model antrenate doar prin etapa întâi izolează efectul modificărilor arhitecturale (capul de incertitudine, automascarea, suprimarea de caracteristici) independent de strategia de augmentare, în timp ce modelul complet antrenat și cu etapa a doua reflectă capacitatea de adaptare la condiții meteorologice nefavorabile."

**CE PUI ÎN LOC** (înlocuiește integral cu):
> "Etapa a doua (S2) nu este o configurație unică, ci un protocol de fine-tuning parametrizat de-a lungul a doi comutatori independenți: activarea augmentărilor de vreme și degradări vizuale (secțiunea 3.5) și activarea suprimării caracteristicilor ghidate de incertitudine (secțiunea 3.4) în calculul funcției de cost. Capul de incertitudine este calibrat (secțiunea 3.3.2) prin funcția de cost $L_{calib}$, independent de cei doi comutatori. Protocolul S2 este aplicat **secvențial, de două ori**: prima rulare pornește de la punctul de control rezultat din etapa S1 — la care capul de incertitudine nu este încă supus calibrării explicite și este predispus colapsului descris în secțiunea 3.3.2 — cu ambii comutatori dezactivați, izolând efectul pur al calibrării incertitudinii și producând modelul **URW-Depth**, optimizat pentru acuratețe maximă pe date curate. A doua rulare continuă fine-tuning-ul **de la rezultatul primei rulări S2** (de la URW-Depth, nu independent de la S1), activând ambii comutatori — augmentările de vreme și suprimarea caracteristicilor — și producând modelul **URW-Depth-Weather**, care valorifică incertitudinea deja calibrată pentru a suprima activ caracteristicile nesigure, tranzacționând o parte din acuratețea pe date curate pentru o robustețe semnificativ crescută la condiții meteorologice nefavorabile și degradări sintetice (secțiunea 4.2). Această înlănțuire (S1 → S2-calibrare → S2-robustețe) reflectă aceeași logică de curriculum progresiv descrisă la începutul secțiunii: incertitudinea trebuie calibrată corect înainte ca suprimarea ghidată de ea să poată fi activată cu folos.
>
> Reutilizarea aceluiași protocol S2, doar cu comutatori diferiți, evită necesitatea unei arhitecturi sau a unei strategii de antrenare separate pentru fiecare variantă și permite, în principiu, extinderea ulterioară la alte puncte de pe curba acuratețe-robustețe prin simpla reconfigurare a celor doi comutatori. Această separare clarifică totodată atribuirea în experimentele din capitolul 4: variantele de model antrenate doar prin etapa întâi izolează efectul modificărilor arhitecturale (capul de incertitudine, calibrarea) independent de strategia de augmentare și de suprimare, în timp ce cele două rulări ale etapei S2 reflectă, separat, contribuția calibrării pure și contribuția combinată calibrare+suprimare+augmentare asupra robusteții la condiții meteorologice nefavorabile."

*(Motiv: textul original descrie S2 ca o singură rulare cu un singur rezultat ("modelul complet antrenat"); de fapt protocolul S2 e rulat de două ori, cu comutatori diferiți pentru augmentare ȚI pentru suprimare, generând cele două variante finale. Aceasta e și motivul pentru numele lor: URW-Depth = S2 fără ambii comutatori; URW-Depth-Weather = S2 cu ambii comutatori activați.)*

---

## 9. Declarația de autenticitate (ultima pagină) — de completat manual

**CE COMPLETEZI** la rândul "În elaborarea lucrării":
> bifează **"am utilizat"**, denumire: **Claude (Anthropic)**, sursa: **Claude Code / API Anthropic**.

Aceasta nu e opțională — conform art. 34 din regulamentul citat în formular, nedeclararea folosirii AI la nivelul la care a fost folosit în acest proiect (implementare cod, depanare, rulare experimente) constituie declarație falsă cu risc de anulare a diplomei.
