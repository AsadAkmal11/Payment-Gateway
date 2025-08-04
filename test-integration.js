// Test script to verify backend-frontend integration
const axios = require('axios');

const API_BASE_URL = 'http://localhost:8000';

async function testBackendConnection() {
  try {
    console.log('🔍 Testing backend connection...');
    
    // Test health endpoint
    const healthResponse = await axios.get(`${API_BASE_URL}/health`);
    console.log('✅ Backend is running:', healthResponse.data);
    
    // Test transaction creation
    const testTransaction = {
      full_name: "Test User",
      email: "test@example.com",
      phone: "+1234567890",
      amount: 99.99
    };
    
    console.log('🔍 Testing transaction creation...');
    const transactionResponse = await axios.post(`${API_BASE_URL}/transactions/create`, testTransaction);
    console.log('✅ Transaction created successfully:', transactionResponse.data);
    
    console.log('🎉 Backend integration test passed!');
    
  } catch (error) {
    console.error('❌ Backend integration test failed:', error.message);
    if (error.response) {
      console.error('Response data:', error.response.data);
    }
  }
}

// Run the test
testBackendConnection(); 