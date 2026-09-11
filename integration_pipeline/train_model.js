import * as tf from '@tensorflow/tfjs-node';

export async function trainModel(data) {
  const model = tf.sequential();
  model.add(tf.layers.dense({ inputShape: [data.inputShape], units: 32, activation: 'relu' }));
  model.add(tf.layers.dense({ units: 16, activation: 'relu' }));
  model.add(tf.layers.dense({ units: 1 }));

  model.compile({ loss: 'meanSquaredError', optimizer: tf.train.adam(0.001) });

  const xs = tf.tensor2d(data.inputs);
  const ys = tf.tensor2d(data.outputs);

  await model.fit(xs, ys, { epochs: 200 });
  await model.save('file://C:/EV_Files/teaka_trading_app/integration/ml/model_output');

  console.log('✅ Model training complete');
}
