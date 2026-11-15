# 30-second video · final text

> Internal note (Spanish): comparación línea por línea del guion original del plan con
> los resultados reales, y texto final. Cambios pedidos por Esteban: ya no se usan datos
> de ESA (solo NASA y JAXA) y "found Pinacate" pasa a "ranked it in its top 3".

## Line-by-line review

| Time | Visual | Original line | Check against real results | Final line |
| --- | --- | --- | --- | --- |
| 0:00 | Logo | "We're Dinamita Buena Onda, from Mexico." | OK | Same |
| 0:02 | Lunar globe spinning | "Before going to the Moon, astronauts train on Earth. But where on Earth is most like the Moon?" | OK | Same |
| 0:05 | The three bodies | "ASTRAL: a star map that finds Earth's twins of the Moon and Mars." | OK (search works from any body; Moon and Mars → Earth is the core story) | Same |
| 0:10 | Click on the south pole, arcs to Mexico, comparison | "Our own neural network, trained on NASA, JAXA and ESA data, found Pinacate, where Apollo astronauts trained, without ever seeing it." | **ESA:** no ESA data is used. **JAXA:** SLDEM2015 (LOLA + Kaguya) is used only for the lunar test queries (Montes Marius), **not for training** and not in this south-pole example; training is NASA only (LOLA, NASADEM, SRTMGL30, MOLA). **"found":** at 60 m the Faustini rim (Artemis III region) returns a held-out patch 12 km from El Pinacate as its **3rd** Earth match; for Montes Marius the median rank is 147 of 55,444. | "Our own neural network, trained on NASA data, ranked Pinacate — where Apollo astronauts trained — in its top 3, without ever seeing it." |
| 0:20 | Terrain galaxy | "It also finds new sites, and explains what matches and what doesn't." | OK: Haworth and Faustini rims return new Mexican sites (Sonora, Chihuahua, Coahuila, Jalisco, Hidalgo); seven dimensions + "not comparable" list; the galaxy is real (`galaxy_60.json`, 3D UMAP) | Same |

**Why "trained on NASA data" and not "NASA and JAXA":** saying the network was trained on
JAXA data would be inaccurate. JAXA is credited where it is true: in the end card and in
the submission page (SLDEM2015 for the lunar test queries). If the team prefers to keep
JAXA in the voice-over, the accurate wording is "built with NASA and JAXA data" — but the
south-pole example on screen does not use JAXA data.

## Final script (English)

| Time | Visual | Voice-over |
| --- | --- | --- |
| 0:00 | Logo | "We're Dinamita Buena Onda, from Mexico." |
| 0:02 | Lunar globe spinning | "Before going to the Moon, astronauts train on Earth. But where on Earth is most like the Moon?" |
| 0:05 | The three bodies | "ASTRAL: a star map that finds Earth's twins of the Moon and Mars." |
| 0:10 | Click the **Faustini rim** (`-87.3, 77.0`), Detail (60 m), arcs to Mexico, open the 3rd card (Sonora, 31.87° N, 113.54° W) | "Our own neural network, trained on NASA data, ranked Pinacate — where Apollo astronauts trained — in its top 3, without ever seeing it." |
| 0:20 | Terrain galaxy | "It also finds new sites, and explains what matches and what doesn't." |

**End card (small text, last 3 s):** "Data: NASA LRO, MGS, Mars Odyssey, SRTM and MODIS ·
JAXA Kaguya (SLDEM2015). Suitability layers are suggestions: illumination and
communications not included."

**On-screen number at 0:10:** "Top 3 · never seen in training". Do not show "#1" for
El Pinacate.

## Notes for the edit

- The click at 0:10 must be the **Faustini rim at 60 m**. Clicking Shackleton or another
  south-pole point does not return El Pinacate in the top 3.
- If a photo of Apollo training at El Pinacate is used, it must be a NASA archive image
  (credit NASA). Any AI-generated image needs a watermark and must not carry the NASA
  logo (challenge rules).
- Optional, only if there is time left in the edit: "From Mars, Olympus Mons finds Mauna
  Loa — first out of 7,669 Earth sites" (network-only validation). It does not fit in
  30 s without cutting another line.
