cd "%~dp0"
call env\Scripts\activate
python unpack.py --config gog_service
echo Script execution completed.
pause
