# Live demo script · 3 minutes

> Internal note (Spanish): guion de la demo en vivo. Lo que se dice va en inglés (lo
> escucha el jurado). Todos los números están verificados contra los artefactos y contra
> la búsqueda real (`release/v2-1km-r4`, RRF, perfil `general`). Los resultados
> precalculados (`frontend/src/mocks/precomputed-results.json`) son idénticos a los de la
> API para estos sitios: si la API falla, el modo **Demo data** muestra lo mismo.
>
> **Antes de empezar:** servidor con `ASTRAL_ARTIFACTS` apuntando a `v2-1km-r4`; interfaz en
> **Live API**; perfil **General**; tener abierta en otra pestaña la figura
> `data/artifacts/figures/validation_dark.png` y `suitability/suitability_mars_candidates.png`.
> Usar **Custom coordinates** (LATITUDE / LONGITUDE) para caer exacto en cada sitio.
> La interfaz aún no expone `scale_mode`: todo el guion usa `same_size` (el valor por defecto).

| Time | Example |
| --- | --- |
| 0:00–0:20 | Hook |
| 0:20–1:00 | 1. Olympus Mons → Mauna Loa |
| 1:00–1:45 | 2. Lunar south pole: Faustini rim → El Pinacate |
| 1:45–2:20 | 3. Montes Marius blind test (validation figure) |
| 2:20–2:50 | 4. Mars landing sites on the suitability layer |
| 2:50–3:00 | Close |

## 0:00–0:20 · Hook

**Show:** the three globes (start screen).

**Say:** "In the 1960s NASA trained the Apollo astronauts at El Pinacate, in Sonora,
because experts thought it looked like the Moon. ASTRAL makes that search systematic:
our own neural network, trained on NASA elevation data, compares terrain across Earth,
the Moon and Mars."

## 0:20–1:00 · 1. Olympus Mons → Mauna Loa

**Clicks:**
1. **Origin:** Mars. **Custom coordinates:** LATITUDE `18.65`, LONGITUDE `-133.8`.
2. **SEARCH IN:** Earth only. **SEARCH SCALE:** Global (1 km). **Explore.**
3. In the result list, click the **Hawaii, USA** card (4th result, 19.59° N, 155.39° W).

**Say:** "This is Olympus Mons, the largest volcano in the solar system. Among Earth's
results, the network brings up Hawaii's shield volcanoes. In our validation, with the
network alone, Mauna Loa ranks **first out of 7,669** Earth terrain patches; a classic
terrain formula puts it at rank **1,720**."

**Show on the card:** terrain score **0.77** for the Hawaii match; then open **Where the
analogy stops**: gravity and atmosphere are not comparable.

> Nota: en la lista con RRF y todas las dimensiones, Hawái sale en el lugar 4 (y otra
> vez en el 6); el "lugar 1" es de la validación con la red sola. Decirlo así.

## 1:00–1:45 · 2. Lunar south pole: Faustini rim → El Pinacate

**Clicks:**
1. **Origin:** Moon. **Custom coordinates:** LATITUDE `-87.3`, LONGITUDE `77.0`
   (Faustini rim, Artemis III candidate region).
2. **SEARCH IN:** Earth. **SEARCH SCALE:** Detail (60 m). **Explore.**
3. Click the 3rd card: **Sonora, Mexico** (31.87° N, 113.54° W).

**Say:** "Now a candidate for the Artemis base at the lunar south pole, at 60-meter
detail. The third Earth match is in Sonora — 12 kilometers from the center of
El Pinacate. The network never saw El Pinacate during training: we hid it on purpose,
as a blind test. It found the Apollo training ground on its own."

**Show:** the card's dimension breakdown (terrain **0.65**, total **0.50**) and the
**Lunar suitability** panel: Faustini rim scores in the **93rd percentile** of the south
pole for landing, roving, ice and temperature.

**Say (limits):** "The suitability layer is a suggestion: illumination and Earth
visibility for communications are not in the challenge data, so we do not claim a site
selection."

## 1:45–2:20 · 3. Blind test, in numbers

**Show:** `validation_dark.png` (other tab).

**Say:** "This is not one lucky example. For the lunar volcanic domes of Montes Marius,
El Pinacate reaches median rank **147 out of 55,444** Earth patches with our network,
versus **320** for the formula and **345** for random — and it lands in the top 50 for
**49 of 195** queries, against 12 for the formula. We also show where it fails: lunar
maria do not match Earth's eroded flood basalts."

## 2:20–2:50 · 4. Mars landing sites on the suitability layer

**Clicks:**
1. **Origin:** Mars. **Custom coordinates:** LATITUDE `-1.95`, LONGITUDE `-5.53`
   (Meridiani Planum, Opportunity). **SEARCH IN:** Earth. **Global (1 km).** **Explore.**
2. Show the first card: **Chubut, Argentina** (terrain **0.85**).
3. Switch to the other tab: `suitability_mars_candidates.png` (or the Mars suitability
   overlay on the globe if the frontend shows it).

**Say:** "On Mars we built a transparent suitability layer from MOLA slope and
elevation and Mars Odyssey hydrogen. The plains where Opportunity, Spirit and InSight
landed all score above the 90th percentile of the planet. Jezero and Gale score near
the middle — they were chosen for science, not for an easy landing. And for Opportunity's
plain, our network's closest Earth terrain is the Patagonian steppe in Chubut."

> Nota de números: la figura y el README usan el promedio en 50 km (Opportunity 95.3,
> Spirit 99.8, InSight 92.7); la API de aptitud muestra el percentil 90 de la zona
> (97.4, 100, 96.3). Si se lee un número en voz alta, usar el de la figura que se muestra.

## 2:50–3:00 · Close

**Say:** "ASTRAL: click anywhere on three worlds, find real analogs, and know exactly
what is similar and what Earth can never reproduce."

## If something fails

- **API down:** switch to **Demo data**. Faustini rim (60 m) and Meridiani Planum (1 km)
  are precomputed with identical results. **Olympus Mons is not precomputed**: in demo
  mode skip example 1 and go from the El Pinacate card (Earth origin `31.77, -113.5`,
  which is precomputed) or show the validation figure for Olympus → Mauna Loa.
- **Detail (60 m) unavailable** for a point: the UI offers **Search globally (1 km)**;
  keep Faustini at 60 m exactly at `-87.3, 77.0`.
