# 05 — Preguntas de entrevista

Preguntas típicas sobre este proyecto y cómo responderlas con seguridad. Practica
diciéndolas en voz alta en inglés también.

## Sobre el mercado

**¿Por qué una subasta doble de precio uniforme y no pagar a cada uno su precio
(pay-as-bid)?**
Porque el precio uniforme es **justo dentro de la hora**: todos los que comercian
pagan o cobran lo mismo, lo cual es fácil de defender ante los participantes.
Pay-as-bid premia adivinar el precio y puede hacer que vecinos paguen precios muy
distintos por la misma energía en la misma hora.

**¿Cómo garantizas que el trato conviene a las dos partes?**
El precio de equilibrio siempre queda entre el precio feed-in (bajo) y el retail
(alto) de la red. Por eso el vendedor cobra más que lo que pagaría la red y el
comprador paga menos que lo que cobraría la red. Además lo reportamos
explícitamente como `buyer_savings` y `seller_earnings`.

**¿Qué pasa con la energía que no se empareja?**
Se comercia con la red: `grid_import` para lo que falta y `grid_export` para lo
que sobra. El mercado local solo cubre lo que encaja a un precio aceptable para
ambos.

## Sobre el pronóstico

**¿Por qué un modelo tan simple (media por hora)?**
Porque es una **línea base** clara y explicable. Define la interfaz y da una
referencia que cualquier modelo más complejo debe superar. En ingeniería, primero
una línea base clara y luego mejoras medibles.

**¿Cómo mides el error y por qué MAE?**
Con el error absoluto medio, en kWh, así que es interpretable directamente ("nos
equivocamos un cuarto de kWh de media por hora"). El MAE es más robusto a errores
puntuales que el RMSE.

**¿Cómo evitas el *data leakage*?**
Entreno con todos los días menos el último y simulo el último. El modelo nunca ve
el día que tiene que predecir.

## Sobre la cadena

**¿Por qué usar blockchain aquí? ¿No es exagerado?**
No usamos la cadena para pagar, sino como un **registro compartido, auditable e
inmutable** de quién dio energía a quién. Varios vecinos que no se fían al 100%
entre sí necesitan una fuente de verdad común que nadie pueda alterar en secreto.
Ese es el caso de uso legítimo.

**¿Por qué enteros (mili-kWh y céntimos)?**
La EVM no tiene decimales y los flotantes acumulan error. Con enteros, la
contabilidad es exacta y todos calculan lo mismo. La división `kWhMilli *
priceCents / 1000` trunca de forma determinista, igual en Solidity y en el fake.

**¿Cómo proteges la privacidad?**
Cada casa es un `bytes32` (hash del nombre). La cadena nunca ve nombres ni datos
personales. La correspondencia id↔persona vive fuera de la cadena.

**¿Por qué `onlyOperator`?**
Solo la cámara de compensación del mercado puede registrar operaciones. Así nadie
puede escribir posiciones falsas. Se complementa con guardas (`ZeroParty`,
`SameParty`, `ZeroEnergy`) mediante errores personalizados, que son baratos en
gas.

## Sobre el diseño y las pruebas

**¿Por qué un `Protocol` para el ledger y un fake en memoria?**
Para desacoplar el mercado de web3. La API funciona con o sin cadena, las pruebas
de mercado son rápidas (sin nodo), y una prueba de equivalencia comprueba que el
fake y el contrato real dan las mismas posiciones, para que el fake no se desvíe.

**¿Cómo compilas el contrato sin un `solc` nativo?**
Con `solc-js` fijado en npm, invocado por `node compile.js`. El artefacto (ABI +
bytecode) se versiona, así que el runtime y las pruebas despliegan el contrato
sin compilador. Builds idénticos en local y en CI.

**¿Qué cubren las pruebas?**
El pronosticador, el mecanismo de mercado, la API HTTP y el contrato (desplegado
en una EVM en memoria, incluyendo las guardas de operador y de entrada). Las
pruebas que despliegan el contrato llevan la marca `chain`. La cobertura mínima
en CI es del 80 %.

## Pregunta trampa

**Si tuvieras que llevar esto a producción, ¿qué cambiarías primero?**
Tres cosas: (1) sustituir el pronóstico de media por uno que use clima y
tendencia, midiendo la mejora contra la línea base; (2) añadir restricciones de
red reales al mercado (límites de capacidad por línea); y (3) endurecer la
gestión de la clave del operador (HSM o firma delegada) y auditar el contrato
antes de desplegarlo en una red pública.
