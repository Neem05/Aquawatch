import tensorflow as tf

model = tf.keras.models.load_model(".\models\water_forecast_model.keras")

model.export("saved_model")