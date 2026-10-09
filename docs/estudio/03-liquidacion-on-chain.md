# 03 — La liquidación en la cadena (on-chain)

## ¿Qué registra el contrato y por qué?

`GridLedger.sol` es un **libro mayor** (ledger): guarda, de forma que nadie puede
alterar sin que se note, quién dio energía a quién, cuánta y a qué precio. Cada
participante puede auditarlo. Esa es la razón de usar una cadena: no un pago
"cripto", sino un **registro compartido y a prueba de manipulación**.

Por cada operación liquidada, el contrato:

1. Emite un evento `TradeSettled` (índice, comprador, vendedor, energía, precio,
   hora).
2. Actualiza la **posición** de cada parte: energía neta (en mili-kWh) y dinero
   neto (en céntimos), más un contador de operaciones.

El comprador suma energía y resta dinero; el vendedor resta energía y suma
dinero. Es contabilidad de doble partida, igual que en un libro contable.

## ¿Por qué enteros y no decimales?

La EVM (la máquina virtual de Ethereum) **no tiene números con decimales**. Y
aunque los tuviera, los decimales acumulan error de redondeo. Si dos vecinos
calcularan su posición de forma ligeramente distinta, no se pondrían de acuerdo
en quién debe qué — justo el problema que el libro compartido quiere evitar.

La solución:

- Energía en **mili-kWh** enteros (1 kWh = 1000).
- Dinero en **céntimos** enteros.
- El contrato calcula `cents = (kWhMilli * priceCents) / 1000` con división
  entera (trunca). Es determinista y da el mismo resultado en Solidity y en el
  fake de Python.

Así la contabilidad es **exacta y reproducible**: todos calculan lo mismo.

## Privacidad: nada de datos personales en la cadena

Una cadena es pública y permanente. Nunca debemos poner ahí el nombre de una
persona o su número de contador. Por eso cada casa se identifica con un
`bytes32`: el **hash keccak** de su nombre (`house_id(name)` en `ledger.py`).

La cadena ve energía, dinero y un identificador opaco. La correspondencia entre
ese identificador y una persona real se queda **fuera de la cadena**, bajo el
control del operador. Esta es una buena práctica general: minimizar los datos
que escribes en un sistema inmutable.

## Solo el operador puede liquidar

El contrato tiene un modificador `onlyOperator`. Solo la "cámara de compensación"
del mercado (el operador) puede registrar una operación. Si otro lo intenta, la
transacción se revierte con el error `NotOperator`. Esto evita que alguien
escriba posiciones falsas.

También hay guardas de entrada con errores personalizados:

- `ZeroParty`: ni comprador ni vendedor pueden ser el id cero.
- `SameParty`: nadie puede comerciar consigo mismo.
- `ZeroEnergy`: no se registran operaciones de 0 energía.

Los **errores personalizados** (en vez de cadenas de texto en `require`) son más
baratos en gas y más fáciles de leer en las pruebas.

## El fake en memoria: por qué existe

En `ledger.py` hay dos clientes que cumplen el mismo `Protocol` (`LedgerClient`):

- `Web3LedgerClient`: habla con el contrato real por JSON-RPC.
- `InMemoryLedgerClient`: imita la contabilidad del contrato en un diccionario,
  con las mismas guardas.

¿Por qué un fake? Para que la API y las pruebas de mercado funcionen **sin
cadena**, rápido y sin levantar un nodo. Y hay una prueba clave
(`test_in_memory_matches_contract`) que liquida la misma operación en el contrato
real y en el fake y comprueba que las posiciones coinciden. Así el fake nunca se
"desvía" del comportamiento real.

## Verificación rápida (lo que comprueban las pruebas)

Liquidar 2,5 kWh a 50 céntimos/kWh:

- `kWhMilli = 2500`, `cents = 2500 * 50 / 1000 = 125`.
- Comprador: energía **+2500**, dinero **−125**.
- Vendedor: energía **−2500**, dinero **+125**.

Eso es exactamente lo que afirman las pruebas, tanto en el contrato como en el
fake.

## Para fijar la idea

- La cadena aporta un **registro auditable e inmutable**, no un pago.
- Enteros (mili-kWh y céntimos) → contabilidad **exacta** y compatible con la EVM.
- Identificadores `bytes32` → **sin datos personales** en la cadena.
- `onlyOperator` + guardas → nadie escribe posiciones falsas.
- El fake, validado contra el contrato, mantiene las pruebas rápidas y fieles al contrato.
