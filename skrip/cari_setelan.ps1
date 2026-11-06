cd D:\2026\bot-peta\skrip
$env:AMBPX='15'
foreach($m in 85,80){ foreach($e in 2,1){ foreach($rm in 30,20){
  $env:MAXV="$m"; $env:ERO="$e"; Remove-Item Env:AROUND -ErrorAction SilentlyContinue
  $c=(python prep.py 004 000102 $rm 2>&1 | Select-String "kandidat") -replace '.*kandidat: (\d+).*','$1'
  $g=(python finish.py 004 000102 "000102_Inset 1,000102" 2000 2>&1 | Select-String "gabungan") -replace ' \| peta.*',''
  "MAXV=$m ERO=$e RM=$rm cand=$c $g"
}}}
