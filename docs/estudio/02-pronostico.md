# 02 — El pronóstico de energía

## ¿Por qué hace falta pronosticar?

El mercado tiene que decidir, **antes** de que pase la hora, quién tendrá
excedente y quién tendrá déficit. No podemos esperar a medir la energía real:
para eso necesitamos una predicción del *neto* de cada casa (generación menos
consumo) para cada hora.

- Neto **positivo** → le sobra energía → será **vendedor**.
- Neto **negativo** → le falta energía → será **comprador**.

## El modelo base: media por hora

El modelo está en `forecast.py` y se llama `HourlyMeanForecaster`. Es a
propósito simple y honesto:

1. En el entrenamiento (`fit`), agrupa el histórico por `(casa, hora_del_día)` y
   calcula la **media** de generación y de consumo.
2. Para predecir (`forecast_net`), resta: `media_generación − media_consumo`
   para esa casa y esa hora.

Es decir: "¿cuánto suele generar y consumir la casa 03 a las 14:00?" La
respuesta es el promedio histórico.

## ¿Por qué empezar con algo tan simple?

Porque es un **buen punto de partida** y es fácil de explicar:

- No tiene parámetros ocultos ni riesgo de sobreajuste raro.
- Sirve de *línea base*: cualquier modelo más complejo debe superarla para
  justificar su complejidad.
- Deja clara la **interfaz**: `fit`, `forecast_net` y `mae`. Un modelo más fuerte
  (por ejemplo, gradient boosting o uno que use el clima) puede sustituirlo sin
  tocar el resto del sistema.

Esta es una idea importante de ingeniería: primero una línea base clara, después
mejoras medibles contra ella.

## Cómo se mide el error

El método `mae` calcula el **error absoluto medio** (Mean Absolute Error): para
cada fila real, toma el valor predicho del neto, calcula la diferencia absoluta
con el neto real y promedia todas esas diferencias.

En la demo, el MAE del neto ronda **0,26 kWh**, lo que para este tamaño de casas
es razonable para un modelo tan simple.

### ¿Por qué MAE y no otra métrica?

- El MAE está en las **mismas unidades** que la energía (kWh), así que es fácil
  de interpretar: "nos equivocamos, en promedio, un cuarto de kWh por hora".
- Es robusto: no castiga de forma exagerada un error puntual grande, como haría
  el error cuadrático (RMSE).

## Cómo encaja con el mercado

`service.py` entrena el pronosticador con todos los días **menos el último** y
usa el último día como el día a simular. Así el modelo nunca "ve" el día que
tiene que predecir: es una separación honesta entre entrenamiento y evaluación.

## Para fijar la idea

- Pronosticar el neto es lo que permite montar el mercado **antes** de medir.
- La media por hora es una línea base clara y explicable.
- La interfaz (`fit` / `forecast_net` / `mae`) permite cambiar el modelo sin
  romper nada más.
- El MAE, en kWh, dice de un vistazo cómo de bueno es el pronóstico.
