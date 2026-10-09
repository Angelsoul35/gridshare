# 01 — El mercado local y la subasta doble

## El problema económico

Imagina una calle con varias casas. Algunas tienen paneles solares (las
llamamos *prosumidores*: producen y consumen) y otras solo consumen. A mediodía,
las casas con paneles suelen producir más de lo que gastan: les sobra energía.
Por la tarde-noche, casi todas gastan más de lo que producen: les falta energía.

Con la red eléctrica tradicional hay dos precios muy distintos:

- **Precio de venta a la red (feed-in):** lo que la red te paga por tu excedente.
  Es **bajo** (en el proyecto, `GS_GRID_SELL_CENTS = 20` céntimos/kWh).
- **Precio de compra a la red (retail):** lo que pagas por la energía que tomas.
  Es **alto** (`GS_GRID_BUY_CENTS = 80` céntimos/kWh).

Ese hueco entre 20 y 80 es la oportunidad. Si dos vecinos comercian a un precio
intermedio, digamos 50:

- El que vende gana **50** en vez de los **20** de la red → gana más.
- El que compra paga **50** en vez de los **80** de la red → paga menos.

Las dos partes salen ganando, y además menos energía viaja por la red general.
Ese es el corazón del proyecto.

## ¿Qué es una subasta doble de precio uniforme?

"Doble" porque hay ofertas de compra **y** de venta al mismo tiempo (en una
subasta normal solo hay un vendedor y muchos compradores). "Precio uniforme"
porque todas las operaciones de esa hora se liquidan al **mismo** precio.

El algoritmo (`market.py`, función `clear_market`) es así:

1. Ordena a los **compradores** por su oferta (*bid*), de mayor a menor.
2. Ordena a los **vendedores** por su precio pedido (*ask*), de menor a mayor.
3. Empareja mientras el comprador actual ofrezca al menos lo que pide el
   vendedor actual (`bid >= ask`).
4. Todo lo emparejado se liquida a un único **precio de equilibrio**: el punto
   medio del último par que se emparejó.
5. Lo que no se empareja (porque ya no hay acuerdo de precio) se comercia con la
   red.

### Un ejemplo pequeño

Compradores (ordenados): A ofrece 70, B ofrece 55.
Vendedores (ordenados): X pide 40, Y pide 60.

- A (70) vs X (40): hay acuerdo (70 ≥ 40). Se emparejan. Precio del par = (70+40)/2 = 55.
- Siguiente: B (55) vs Y (60): no hay acuerdo (55 < 60). Se detiene.

El precio de equilibrio del último par emparejado fue 55, así que **todo** lo
emparejado se liquida a 55 céntimos/kWh.

## ¿Por qué un margen por casa?

En `service.py`, cada casa añade un pequeño margen determinista (de 0 a 15) a su
oferta: el comprador ofrece un poco por debajo del precio retail y el vendedor
pide un poco por encima del precio feed-in. Sin ese margen, todas las ofertas
serían idénticas y el precio de equilibrio siempre caería en el mismo sitio. El
margen hace que el mercado sea más realista y que el precio varíe según la hora.

Es *determinista* (se calcula con la suma de los códigos de las letras del
nombre de la casa) para que las pruebas den siempre el mismo resultado.

## Qué devuelve el mercado

`MarketResult` incluye:

- `trades`: la lista de operaciones (comprador, vendedor, kWh, precio).
- `clearing_price`: el precio único de la hora.
- `p2p_kwh`: cuánta energía se comerció entre vecinos.
- `grid_import_kwh` / `grid_export_kwh`: lo que no se emparejó y fue a la red.
- `buyer_savings_cents` / `seller_earnings_cents`: el ahorro de cada lado frente
  a comerciar solo con la red.

## Validación con datos reales (consumo de Londres + solar de Alemania)

El mercado es **determinista** (una subasta doble y aritmética de tarifa, no un
modelo entrenado), así que aquí no hay "exactitud" ni over/underfitting que medir. La
pregunta correcta es otra: *¿el mecanismo produce resultados sensatos y valiosos sobre
datos reales, no solo sobre el generador sintético?* Para responderla, GridShare corre
sobre un vecindario **real**:

- **Consumo:** consumo horario real de hogares del ensayo Low Carbon London
  (contadores inteligentes), un hogar real por casa.
- **Generación:** un **factor de capacidad solar** real (0 de noche, ≈1 al mediodía
  solar) medido de la producción fotovoltaica de la red alemana, escalado por el tamaño
  de panel de cada prosumidor.

Con `python -m gridshare.real_benchmark`:

```
vecindario         : 20 casas, 10 con paneles, 14 días reales
tarifa de red      : compra 80c / venta 20c por kWh
comercio P2P       : 71,5 kWh en el día
autosuficiencia    : 27,9 % de la demanda cubierta localmente
precio de equilibrio: 48,8c de media (todos dentro del rango 20-80c)
ahorro comprador   : 23,05 $ frente al precio de red
ganancia vendedor  : 19,85 $ frente al feed-in
```

### La invariante económica, comprobada sobre dato real

La propiedad que hace útil a un mercado local es que **las dos partes ganan**: el
precio de equilibrio cae *dentro* del margen entre el feed-in (lo que paga la red por
exportar, 20c) y el retail (lo que cobra la red por importar, 80c). Entonces:

- el **vendedor** cobra `precio − feed-in > 0` por cada kWh vendido localmente;
- el **comprador** paga `retail − precio > 0` menos que a la red.

`tests/test_real_benchmark.py` lo comprueba de forma **funcional** sobre el vecindario
real: la identidad contable (`net = generación − consumo`), que todo precio de
equilibrio queda dentro del rango, y que ambos ahorros son positivos. Y lo prueba por
contraste (estilo mutación): si se **cierra el margen** (compra = venta), la ventaja
desaparece y los ahorros caen a cero — demostrando que el valor viene del margen, no de
un artefacto del código.

## Para fijar la idea

- La subasta doble es **justa dentro de la hora**: todos pagan o cobran lo mismo.
- El precio de equilibrio siempre queda **entre** el precio feed-in y el retail,
  por eso las dos partes ganan.
- `clear_market` es una **función pura**: mismas entradas, mismas salidas. Eso la
  hace fácil de probar y de reemplazar por otro mecanismo más adelante.
- Al ser determinista, "datos reales" aquí significa **correr el mercado sobre perfiles
  reales** de consumo y generación y comprobar que los resultados son correctos y
  valiosos, no medir una exactitud de modelo.
