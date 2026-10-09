# Datasets

## `neighbourhood_real.npz` — a real neighbourhood (consumption + solar)

Real measurements used to run the GridShare market on data no one designed (see
*Validated on real meter data* in the top-level README). GridShare needs a per-house
hourly generation and consumption history; this file provides the two real ingredients,
and `gridshare.real_data.load_real_neighbourhood` assembles them into that history.

**Consumption.** Real hourly household electricity use from the Low Carbon London
smart-meter trial, via the Hugging Face mirror
[`eeJunCao/London_smart_meter`](https://huggingface.co/datasets/eeJunCao/London_smart_meter).
Half-hourly kWh readings are summed to hourly kWh. One real metered home per house.

**Solar.** A real solar **capacity factor** (0 at night, ~1 at solar noon) derived from
measured German grid PV output, via
[`sashamn/germany-solar-generation`](https://huggingface.co/datasets/sashamn/germany-solar-generation)
(50Hertz zone, a summer fortnight). The MW series is divided by its 99th percentile to
give a 0–1 profile; each prosumer's generation is that profile times its panel size.

**Arrays.**

| Key           | Shape        | Meaning                                            |
| ------------- | ------------ | -------------------------------------------------- |
| `consumption` | `(20, 336)`  | real hourly consumption (kWh), 20 homes × 14 days  |
| `solar_cf`    | `(336,)`     | real solar capacity factor, 0–1, 14 days hourly    |
| `home_ids`    | `(20,)`      | the London trial home ids used                     |

Each simulated house therefore pairs one real consumption trace with a real solar shape
scaled to its panels — a real-data basis for the local energy market. This is a market
*simulation* on real inputs, not a claim that these specific homes traded with each
other.

### Regenerating

```bash
python -c "from gridshare.real_data import fetch_neighbourhood; print(fetch_neighbourhood())"
```

Needs outbound access to `datasets-server.huggingface.co`. The licences and terms of the
Low Carbon London data and the German solar-generation dataset apply; this slice is
vendored for reproducible benchmarking only.
