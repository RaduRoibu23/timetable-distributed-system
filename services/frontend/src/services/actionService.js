import * as apiService from './apiService';
import { formatResponse } from '../utils/formatters';
import { rolesFromToken } from './authService';

export async function performAction(action, accessToken) {
  console.log('Executing action:', action);
  
  const method = action.method || 'GET';
  let apiPath = action.apiPath;
  
  // Handle dynamic IDs for update/delete operations
  if (action.requiresId && apiPath.includes('{id}')) {
    const listPath = action.getIdFrom || apiPath.replace('/{id}', '').replace('{id}', '').replace(/\/$/, '');
    const listData = await apiService.apiGet(listPath, accessToken);
    
    if (!Array.isArray(listData) || listData.length === 0) {
      throw new Error(`Nu există elemente disponibile pentru ${action.label}. Creează mai întâi un element.`);
    }
    
    const firstId = listData[0].id;
    apiPath = apiPath.replace('{id}', firstId);
    console.log(`Using ID ${firstId} for ${action.label}`);
  }
  
  // Handle class_id requirement for /timetables/me (non-students)
  if (action.requiresClassId && apiPath.includes('/timetables/me')) {
    const roles = rolesFromToken(accessToken);
    if (!roles.includes('student')) {
      const classes = await apiService.apiGet('/classes', accessToken);
      if (Array.isArray(classes) && classes.length > 0) {
        const classId = classes[0].id;
        apiPath = `${apiPath}?class_id=${classId}`;
        console.log(`Using class_id ${classId} for ${action.label}`);
      } else {
        throw new Error('Nu există clase disponibile. Creează mai întâi o clasă.');
      }
    }
  }
  
  // Get body (call function if it's a function, otherwise use as-is)
  let body = null;
  if (action.body) {
    if (typeof action.body === 'function') {
      // Create a bound apiGet function
      const boundApiGet = (path) => apiService.apiGet(path, accessToken);
      body = await action.body(boundApiGet);
    } else {
      body = action.body;
    }
  }
  
  let data;
  console.log(`Calling ${method} ${apiPath}`, body ? `with body: ${JSON.stringify(body)}` : '');
  
  if (method === 'GET') {
    data = await apiService.apiGet(apiPath, accessToken);
  } else if (method === 'POST') {
    data = await apiService.apiPost(apiPath, body || {}, accessToken);
  } else if (method === 'PUT') {
    data = await apiService.apiPut(apiPath, body || {}, accessToken);
  } else if (method === 'PATCH') {
    data = await apiService.apiPatch(apiPath, body || {}, accessToken);
  } else if (method === 'DELETE') {
    data = await apiService.apiDelete(apiPath, accessToken);
  } else {
    data = await apiService.apiGet(apiPath, accessToken);
  }
  
  console.log('Response:', data);
  
  // Format response
  return formatResponse(action.id, data);
}
