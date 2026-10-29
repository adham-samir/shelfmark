// Run with mongosh from the repository root against an explicit database URI.
// Updates validation/index definitions only; never deletes catalog documents.
const fs = require('fs');
const schemaPath = process.env.CATALOG_SCHEMA_PATH || 'database/catalog/product.schema.json';
const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf8'));
const options = {
  validator: { $jsonSchema: schema },
  validationLevel: 'strict',
  validationAction: 'error',
};

if (db.getCollectionNames().includes('products')) {
  const result = db.runCommand({ collMod: 'products', ...options });
  if (result.ok !== 1) {
    throw new Error('Catalog validator update failed: ' + JSON.stringify(result));
  }
} else {
  db.createCollection('products', options);
}

db.products.createIndex({ categories: 1, _id: 1 }, { name: 'category_product_id' });
print('Product catalog schema and indexes applied to ' + db.getName());
