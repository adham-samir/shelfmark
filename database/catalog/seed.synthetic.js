// Synthetic catalog fixtures. Run only against an explicitly selected development database.
const now = new Date();
const products = [
  {
    _id: '10000000-0000-4000-8000-000000000001', name: 'X1 Phone',
    description: 'Synthetic bilingual-ready smartphone fixture.',
    categories: ['phones'],
    attributes: {
      brand: 'X-Series', screen: '6.6 in', storage: '128 GB', memory: '8 GB',
      camera: '50 MP dual, OIS', os: 'Android 15',
      battery: '5000 mAh, 33 W charging', refresh_rate: '120 Hz',
    },
    images: [],
  },
  {
    _id: '10000000-0000-4000-8000-000000000002', name: 'Y2 Phone',
    description: 'Synthetic higher-storage smartphone fixture.',
    categories: ['phones'],
    attributes: {
      brand: 'Y-Series', screen: '6.7 in', storage: '256 GB', memory: '12 GB',
      camera: '108 MP triple, OIS', os: 'Android 15',
      battery: '5400 mAh, 45 W charging', refresh_rate: '120 Hz',
    },
    images: [],
  },
  {
    _id: '10000000-0000-4000-8000-000000000003', name: 'H1 Headphones',
    description: 'Synthetic wireless headphone fixture.',
    categories: ['headphones'],
    attributes: {
      brand: 'H-Series', connectivity: 'Bluetooth 5.3', battery: '30 h',
      feature: 'Noise cancelling', microphone: 'Dual beamforming',
      drivers: '40 mm dynamic', weight: '253 g',
    },
    images: [],
  },
  {
    _id: '10000000-0000-4000-8000-000000000004', name: 'L1 Laptop',
    description: 'Synthetic portable-computer fixture.',
    categories: ['laptops'],
    attributes: {
      brand: 'L-Series', screen: '15.6 in', storage: '512 GB SSD', memory: '16 GB',
      gpu: 'Integrated', os: 'Windows 11 Home', battery: '12 h', weight: '1.7 kg',
    },
    images: [],
  },
  {
    _id: '10000000-0000-4000-8000-000000000005', name: 'X2 Phone',
    description: 'Synthetic smartphone fixture with the larger storage tier.',
    categories: ['phones'],
    attributes: {
      brand: 'X-Series', screen: '6.6 in', storage: '256 GB', memory: '8 GB',
      camera: '64 MP dual, OIS', os: 'Android 14',
      battery: '4800 mAh, 25 W charging', refresh_rate: '90 Hz',
    },
    images: [],
  },
  {
    _id: '10000000-0000-4000-8000-000000000006', name: 'Z3 Phone',
    description: 'Synthetic compact smartphone fixture.',
    categories: ['phones'],
    attributes: {
      brand: 'Z-Series', screen: '6.1 in', storage: '256 GB', memory: '6 GB',
      camera: '12 MP dual', os: 'Android 14',
      battery: '4200 mAh, 20 W charging', refresh_rate: '60 Hz',
    },
    images: [],
  },
  {
    _id: '10000000-0000-4000-8000-000000000007', name: 'Q4 Phone',
    description: 'Synthetic smartphone fixture currently held out of stock for availability testing.',
    categories: ['phones'],
    attributes: {
      brand: 'Q-Series', screen: '6.7 in', storage: '256 GB', memory: '6 GB',
      camera: '48 MP triple', os: 'Android 14',
      battery: '5000 mAh, 18 W charging', refresh_rate: '90 Hz',
    },
    images: [],
  },
  {
    _id: '10000000-0000-4000-8000-000000000008', name: 'H2 Headphones',
    description: 'Synthetic over-ear headphone fixture.',
    categories: ['headphones'],
    attributes: {
      brand: 'H-Series', connectivity: 'Bluetooth 5.3', battery: '30 h',
      feature: 'Noise cancelling', microphone: 'Dual beamforming',
      drivers: '42 mm dynamic', weight: '265 g',
    },
    images: [],
  },
  {
    _id: '10000000-0000-4000-8000-000000000009', name: 'H3 Headphones',
    description: 'Synthetic in-ear headphone fixture with a shorter battery rating.',
    categories: ['headphones'],
    attributes: {
      brand: 'H-Series', connectivity: 'Bluetooth 5.3', battery: '24 h',
      feature: 'Noise cancelling', microphone: 'Single mic',
      drivers: '10 mm dynamic', weight: '5 g each',
    },
    images: [],
  },
  {
    _id: '10000000-0000-4000-8000-000000000010', name: 'H4 Headphones',
    description: 'Synthetic wired headphone fixture without active noise cancelling.',
    categories: ['headphones'],
    attributes: {
      brand: 'H-Series', connectivity: 'Wired', battery: 'Not applicable',
      feature: 'Standard audio', microphone: 'Inline mic',
      drivers: '40 mm dynamic', weight: '240 g',
    },
    images: [],
  },
  {
    _id: '10000000-0000-4000-8000-000000000011', name: 'L2 Laptop',
    description: 'Synthetic compact portable-computer fixture.',
    categories: ['laptops'],
    attributes: {
      brand: 'L-Series', screen: '14.6 in', storage: '256 GB SSD', memory: '16 GB',
      gpu: 'Integrated', os: 'Windows 11 Home', battery: '15 h', weight: '1.3 kg',
    },
    images: [],
  },
  {
    _id: '10000000-0000-4000-8000-000000000012', name: 'L3 Laptop',
    description: 'Synthetic large-screen portable-computer fixture.',
    categories: ['laptops'],
    attributes: {
      brand: 'L-Series', screen: '16.6 in', storage: '1 TB SSD', memory: '32 GB',
      gpu: 'Dedicated 8 GB', os: 'Windows 11 Pro', battery: '9 h', weight: '2.2 kg',
    },
    images: [],
  },
  {
    _id: '10000000-0000-4000-8000-000000000013', name: 'L4 Laptop',
    description: 'Synthetic high-memory portable-computer fixture.',
    categories: ['laptops'],
    attributes: {
      brand: 'L-Series', screen: '15.6 in', storage: '512 GB SSD', memory: '32 GB',
      gpu: 'Integrated', os: 'Windows 11 Home', battery: '11 h', weight: '1.8 kg',
    },
    images: [],
  },
].map(product => ({
  ...product,
  provenance: { kind: 'synthetic', dataset_id: 'stage3-catalog-v3' },
  created_at: now,
  updated_at: now,
}));

for (const product of products) {
  db.products.replaceOne({ _id: product._id }, product, { upsert: true });
}
print('Upserted ' + products.length + ' synthetic catalog products into ' + db.getName());
