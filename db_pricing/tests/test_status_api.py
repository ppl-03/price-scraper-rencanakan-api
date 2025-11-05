from django.test import TestCase, Client
import json


class TestDatabaseStatusAPI(TestCase):
    
    def setUp(self):
        self.client = Client()
    
    def test_db_status_endpoint_exists(self):
        response = self.client.get('/api/db-status/')
        self.assertNotEqual(response.status_code, 404)
    
    def test_db_status_returns_json(self):
        response = self.client.get('/api/db-status/')
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_db_status_has_connection_info(self):
        response = self.client.get('/api/db-status/')
        data = json.loads(response.content)
        
        self.assertIn('connection', data)
        self.assertIn('connected', data['connection'])
        self.assertIn('database', data['connection'])
        self.assertIn('host', data['connection'])
        self.assertIn('error', data['connection'])
    
    def test_db_status_has_table_info(self):
        response = self.client.get('/api/db-status/')
        data = json.loads(response.content)
        
        self.assertIn('gemilang_table', data)
        self.assertIn('exists', data['gemilang_table'])
        self.assertIn('columns', data['gemilang_table'])
        self.assertIn('error', data['gemilang_table'])
    
    def test_db_status_has_overall_status(self):
        response = self.client.get('/api/db-status/')
        data = json.loads(response.content)
        
        self.assertIn('overall_status', data)
        self.assertIn(data['overall_status'], ['healthy', 'unhealthy'])
    
    def test_db_status_returns_200_when_healthy(self):
        response = self.client.get('/api/db-status/')
        data = json.loads(response.content)
        
        if data['overall_status'] == 'healthy':
            self.assertEqual(response.status_code, 200)
    
    def test_db_status_connection_successful(self):
        response = self.client.get('/api/db-status/')
        data = json.loads(response.content)
        
        self.assertTrue(data['connection']['connected'])
        self.assertIsNone(data['connection']['error'])
    
    def test_db_status_table_exists(self):
        response = self.client.get('/api/db-status/')
        data = json.loads(response.content)
        
        self.assertTrue(data['gemilang_table']['exists'])
        self.assertIsNone(data['gemilang_table']['error'])
    
    def test_db_status_table_has_columns(self):
        response = self.client.get('/api/db-status/')
        data = json.loads(response.content)
        
        self.assertIsInstance(data['gemilang_table']['columns'], list)
        self.assertGreater(len(data['gemilang_table']['columns']), 0)
