# Test all One Piece images with production identifier
# Runs identification on each image and saves results

$testImages = Get-ChildItem "test-images/one-piece/" -Include *.png,*.jpg -Recurse
$results = @()

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "TESTING ALL ONE PIECE IMAGES" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

Write-Host "Found $($testImages.Count) test images`n"

foreach ($image in $testImages) {
    Write-Host "Testing: $($image.Name)" -ForegroundColor Yellow
    Write-Host "----------------------------------------------------------------"
    
    # Run identification and capture output
    $output = python scripts/identification/production_card_identifier.py $image.FullName 2>&1
    
    # Parse output for key info
    $cardName = ($output | Select-String "Best Match: (.+)" | ForEach-Object { $_.Matches.Groups[1].Value })
    $confidence = ($output | Select-String "Confidence: (\w+)" | ForEach-Object { $_.Matches.Groups[1].Value })
    $finalScore = ($output | Select-String "Final Score: ([\d.]+)" | ForEach-Object { $_.Matches.Groups[1].Value })
    $totalTime = ($output | Select-String "Total: (\d+)ms" | ForEach-Object { $_.Matches.Groups[1].Value })
    
    # Show summary
    $emoji = if ($confidence -eq "HIGH") { "✅" } elseif ($confidence -eq "MODERATE") { "⚠️" } else { "❌" }
    Write-Host "$emoji $($image.Name): $confidence ($finalScore) - $cardName" -ForegroundColor $(if ($confidence -eq "HIGH") { "Green" } elseif ($confidence -eq "MODERATE") { "Yellow" } else { "Red" })
    Write-Host "   Time: $totalTime ms`n"
    
    # Store result
    $results += [PSCustomObject]@{
        Image = $image.Name
        Card = $cardName
        Confidence = $confidence
        Score = [double]$finalScore
        Time = [int]$totalTime
    }
}

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# Calculate statistics
$highCount = ($results | Where-Object { $_.Confidence -eq "HIGH" }).Count
$moderateCount = ($results | Where-Object { $_.Confidence -eq "MODERATE" }).Count
$lowCount = ($results | Where-Object { $_.Confidence -eq "LOW" }).Count
$avgScore = ($results | Measure-Object -Property Score -Average).Average
$avgTime = ($results | Measure-Object -Property Time -Average).Average

Write-Host "Total Images: $($results.Count)"
Write-Host "HIGH: $highCount ($([math]::Round($highCount / $results.Count * 100, 1))%)" -ForegroundColor Green
Write-Host "MODERATE: $moderateCount ($([math]::Round($moderateCount / $results.Count * 100, 1))%)" -ForegroundColor Yellow
Write-Host "LOW: $lowCount ($([math]::Round($lowCount / $results.Count * 100, 1))%)" -ForegroundColor Red
Write-Host "Average Score: $([math]::Round($avgScore, 3))"
Write-Host "Average Time: $([math]::Round($avgTime, 0))ms`n"

# Save results to JSON
$results | ConvertTo-Json | Out-File "scripts/identification/all_images_test_results.json"
Write-Host "Results saved to: scripts/identification/all_images_test_results.json" -ForegroundColor Cyan

# Show detailed results
Write-Host "`nDetailed Results:" -ForegroundColor Cyan
$results | Format-Table -AutoSize

Write-Host "`n================================================================`n" -ForegroundColor Green


