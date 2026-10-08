# 04 — Arquitectura y decisiones de diseño

## Las capas, de principio a fin

```
 medidores  →  pronóstico  →  mercado  →  orquestación  →  cadena
 generate.py   forecast.py    market.py   service.py       chain/ + contracts/
```

1. **Medidores (`generate.py`).** Genera datos sintéticos y deterministas de
   generación y consumo por casa y por hora. La mitad de las casas tienen
   paneles; el resto solo consumen.
2. **Pronóstico (`forecast.py`).** Predice el neto de cada casa por hora (ver la
   guía 02).
3. **Mercado (`market.py`).** La subasta doble de precio uniforme (ver la guía
   01). Es una función pura.
4. **Orquestación (`service.py`).** Une todo: construye las órdenes a partir del
   pronóstico, llama al mercado y liquida cada operación en la cadena.
5. **Cadena (`chain/ledger.py`, `contracts/`).** El contrato y sus clientes (ver
   la guía 03).

Por encima hay dos formas de usarlo: la **API HTTP** (`main.py`, con FastAPI) y
la **CLI** (`cli.py`, que hace una demo de principio a fin contra una EVM en
memoria).

## Decisión 1: el contrato es opcional

El servicio, la API y la CLI dependen de un `Protocol` (`LedgerClient`), no de
web3 directamente. Gracias a eso, la API puede funcionar **sin cadena** (con el
fake en memoria) o **con cadena** (con el cliente real), sin cambiar nada más.

Esta es la idea de **inversión de dependencias**: el código de alto nivel
(mercado) no depende de un detalle de bajo nivel (web3), sino de una interfaz.

## Decisión 2: funciones puras donde se pueda

`clear_market` no toca la red, ni la cadena, ni el reloj: recibe listas de
órdenes y devuelve un resultado. Eso la hace trivial de probar y fácil de
razonar. Los efectos secundarios (hablar con la cadena) quedan aislados en
`service.py` y en los clientes de `ledger.py`.

## Decisión 3: compilar con solc-js y versionar el artefacto

El contrato se compila con `solc-js` (fijado en `contracts/package.json`) a
través de `node contracts/compile.js`. No hace falta instalar un `solc` nativo, y
la compilación es idéntica en tu portátil y en CI.

El artefacto resultante (ABI + bytecode) se **guarda en el repositorio**. Así el
runtime y las pruebas pueden desplegar el contrato en cualquier nodo **sin
compilador**. Si cambia el contrato, se regenera con `make compile` y el cambio
de bytecode aparece en el diff (es revisable).

## Decisión 4: configuración por variables de entorno

`config.py` usa `pydantic-settings` con prefijo `GS_`. Nunca se escribe una clave
privada en el código; para uso local se deja vacía y se usa la EVM en memoria.
Esto sigue el principio de los *doce factores*: la configuración vive en el
entorno, no en el código.

## Cómo fluye una hora (resumen)

1. `service._orders_for_hour(hour)` construye las órdenes: déficit → oferta de
   compra por debajo del retail; excedente → oferta de venta por encima del
   feed-in; con un pequeño margen por casa.
2. `clear_market(...)` empareja y devuelve el `MarketResult`.
3. Por cada operación, `service` llama a `ledger.settle(...)` con energía en
   mili-kWh y precio en céntimos.
4. La API o la CLI devuelven el resumen: energía P2P, precio, ahorros,
   operaciones liquidadas en la cadena.

## Puntos de extensión

- **Modelo de pronóstico:** cambiar `HourlyMeanForecaster` por uno mejor, con la
  misma interfaz.
- **Mecanismo de mercado:** cambiar `clear_market` por otra subasta (precio de
  reserva, restricciones de red...).
- **Destino de liquidación:** apuntar `GS_CHAIN_RPC_URL` y `GS_CONTRACT_ADDRESS`
  a un nodo real para liquidar en una cadena de verdad.

## Para fijar la idea

- Capas claras y una interfaz entre el mercado y la cadena → la cadena es
  opcional y fácil de probar.
- Funciones puras para la lógica, efectos aislados para la red y la cadena.
- Artefacto del contrato versionado → builds reproducibles y sin compilador en
  tiempo de ejecución.
