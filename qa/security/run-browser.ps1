$ErrorActionPreference='Stop'
$run=[guid]::NewGuid().ToString('N')
$repo=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $repo
try {
 New-Item -ItemType Directory .artifacts -Force | Out-Null
 $envFile=Join-Path $repo '.artifacts/security-qa.env'
 if(-not (Test-Path $envFile)){
  $service=[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
  $django=[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
  [IO.File]::WriteAllText($envFile,"SECURITY_QA_SERVICE_TOKEN=$service`nSECURITY_QA_DJANGO_KEY=$django`n")
  $service=$null;$django=$null
 }
 $compose=@('compose','--env-file',$envFile,'-p','security-revocation-qa','-f','qa/security/compose.yml','-f','qa/security/compose.browser.yml')
 & docker @compose up -d
 if($LASTEXITCODE){throw 'QA startup failed'}
 & docker exec security-revocation-qa-database-1 pg_dump -Fc -U security_qa -f "/tmp/security-before-$run.dump" security_qa
 if($LASTEXITCODE){throw 'QA backup failed'}
 & docker exec security-revocation-qa-database-1 pg_restore --list "/tmp/security-before-$run.dump" | Out-Null
 if($LASTEXITCODE){throw 'QA backup validation failed'}
 & docker cp "security-revocation-qa-database-1:/tmp/security-before-$run.dump" ".artifacts/security-before-$run.dump"
 & docker exec security-revocation-qa-backend-1 python manage.py migrate --noinput
 if($LASTEXITCODE){throw 'QA migration failed'}
 Get-Content qa/security/prepare.py | & docker exec -i security-revocation-qa-backend-1 python manage.py shell
 if($LASTEXITCODE){throw 'QA fixture failed'}
 for($attempt=0;$attempt -lt 120;$attempt++){
  $front=(& docker logs --tail 4 security-revocation-qa-frontend-1 2>&1) -join "`n"
  $gateway=(& docker logs --tail 2 security-revocation-qa-gateway-1 2>&1) -join "`n"
  if($front.Contains('4173') -and $gateway.Contains('ISOLATED_REALTIME_READY')){break}
  Start-Sleep -Seconds 1
 }
 if($attempt -eq 120){throw 'QA node services not ready'}
 & docker exec security-revocation-qa-nginx-1 nginx -t
 if($LASTEXITCODE){throw 'QA proxy configuration invalid'}
 & docker exec security-revocation-qa-nginx-1 nginx -s reload
 if($LASTEXITCODE){throw 'QA proxy reload failed'}
 & docker network disconnect security-revocation-qa_install security-revocation-qa-frontend-1
 & docker network disconnect security-revocation-qa_install security-revocation-qa-gateway-1
 $out=Join-Path $repo '.artifacts'
 $tests=Join-Path $repo 'qa/security'
 $arguments=@('run','--rm','--network','security-revocation-qa_default',
  '--mount',"`"type=bind,source=$tests,target=/tests,readonly`"",'--mount',"`"type=bind,source=$out,target=/evidence`"",
  '--mount','source=crm-audit-playwright-tools,target=/tools,readonly','-e','GLOBAL_AUTH_ISOLATED_QA=1','-e',"GLOBAL_AUTH_RUN_ID=$run",
  'mcr.microsoft.com/playwright:v1.58.2-noble','node','/tests/browser.cjs')
 $process=Start-Process docker -ArgumentList $arguments -PassThru -WindowStyle Hidden -RedirectStandardOutput ".artifacts/browser-$run.log" -RedirectStandardError ".artifacts/browser-$run.err"
 foreach($width in @(1440,768,390)){
  for($wait=0;$wait -lt 240;$wait++){
   if(Test-Path ".artifacts/revoke-requested-$run-$width"){break}
   if($process.HasExited){throw 'Browser exited before controller request'}
   Start-Sleep -Milliseconds 500
  }
  if($wait -eq 240){throw 'Browser controller request timed out'}
  $python="from django.conf import settings; from django.core.management import call_command; from usuarios.models import Credenciales; assert settings.DEBUG and settings.DATABASES['default']['NAME']=='security_qa'; u=Credenciales.objects.get(usuario='security-browser-fixture'); call_command('revoke_all_sessions',reason='browser_test',operation_id='browser-$run-$width',actor_id=u.pk)"
  & docker exec security-revocation-qa-backend-1 python manage.py shell -c $python
  if($LASTEXITCODE){throw 'QA revocation failed'}
  Set-Content ".artifacts/revoke-done-$run-$width" done
 }
 $process.WaitForExit()
 Get-Content ".artifacts/browser-$run.log"
 Get-Content ".artifacts/browser-$run.err"
 if($process.ExitCode){throw 'Browser failed'}
} finally { Pop-Location }
