function getSheet() {
  return SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
}

function doPost(e) {
  var sheet = getSheet();
  var params;
  try {
    params = JSON.parse(e.postData.contents);
  } catch(err) {
    return ContentService.createTextOutput(JSON.stringify({'status': 'error', 'message': 'Invalid JSON'}))
                         .setMimeType(ContentService.MimeType.JSON);
  }
  
  // 이메일 소문자 정규화 + 공백 제거
  var email = (params.email || '').trim().toLowerCase();
  var action = params.action || 'subscribe';
  
  if(!email) {
    return ContentService.createTextOutput(JSON.stringify({'status': 'error', 'message': 'Email required'}))
                         .setMimeType(ContentService.MimeType.JSON);
  }
  
  var data = sheet.getDataRange().getValues();
  var found = false;
  
  // 데이터가 아예 없는 경우 첫 줄(헤더) 추가
  if (data.length === 0 || (data.length === 1 && data[0][0] === '')) {
    sheet.appendRow(["가입일", "이메일", "상태", "취소일"]);
    data = sheet.getDataRange().getValues();
  }
  
  if (action === 'unsubscribe') {
    for (var i = 1; i < data.length; i++) {
      // 대소문자 구분 없이 이메일 비교
      if ((data[i][1] || '').toString().trim().toLowerCase() === email) {
        sheet.getRange(i + 1, 3).setValue('구독취소');
        sheet.getRange(i + 1, 4).setValue(new Date()); // D열에 취소 시간 기록
        found = true;
        break;
      }
    }
    return ContentService.createTextOutput(JSON.stringify({'status': 'success', 'message': '구독 취소 완료', 'found': found}))
                         .setMimeType(ContentService.MimeType.JSON);
    
  } else {
    // subscribe
    for (var i = 1; i < data.length; i++) {
      if ((data[i][1] || '').toString().trim().toLowerCase() === email) {
        if (data[i][2] !== '구독중') {
          sheet.getRange(i + 1, 3).setValue('구독중'); // 재구독 시 상태 변경
          sheet.getRange(i + 1, 4).setValue('');       // 취소일 초기화
        }
        found = true;
        break;
      }
    }
    
    if (!found) {
      var timestamp = new Date();
      sheet.appendRow([timestamp, email, '구독중', '']);
    }
    
    return ContentService.createTextOutput(JSON.stringify({'status': 'success', 'message': '구독 완료'}))
                         .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  var sheet = getSheet();
  var action = e.parameter.action;
  
  // 봇이 메일 발송 전, "구독중"인 이메일 리스트를 요청할 때
  if (action === 'get_subscribers') {
    var data = sheet.getDataRange().getValues();
    var subscribers = [];
    for (var i = 1; i < data.length; i++) {
      if (data[i][2] === '구독중') {
        subscribers.push(data[i][1]);
      }
    }
    return ContentService.createTextOutput(JSON.stringify({'status': 'success', 'data': subscribers}))
                         .setMimeType(ContentService.MimeType.JSON);
  }
  
  // 사용자가 이메일에서 "구독취소" 링크를 눌렀을 때 (GET)
  if (action === 'unsubscribe') {
    var email = (e.parameter.email || '').trim().toLowerCase();
    if (email) {
      var data = sheet.getDataRange().getValues();
      var found = false;
      for (var i = 1; i < data.length; i++) {
        if ((data[i][1] || '').toString().trim().toLowerCase() === email) {
          sheet.getRange(i + 1, 3).setValue('구독취소');
          sheet.getRange(i + 1, 4).setValue(new Date()); // D열에 취소 시간 기록
          found = true;
          break;
        }
      }
      var html = '<div style="max-width: 500px; margin: 40px auto; font-family: sans-serif; text-align: center;">' +
                 '<h2 style="color: #334155;">구독이 성공적으로 취소되었습니다.</h2>' +
                 '<p style="color: #64748B;">더 이상 알바단지 뉴스레터가 발송되지 않습니다. 그동안 함께해주셔서 감사합니다!</p>' +
                 '</div>';
      return ContentService.createTextOutput(html)
                           .setMimeType(ContentService.MimeType.HTML);
    }
    return ContentService.createTextOutput('잘못된 접근입니다.')
                         .setMimeType(ContentService.MimeType.HTML);
  }
  
  return ContentService.createTextOutput('정상 작동중');
}
