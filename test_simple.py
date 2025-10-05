import sys
sys.path.insert(0, 'src')
try:
    import viewer
    print('SUCCESS: viewer module imported')
except Exception as e:
    print(f'ERROR importing viewer: {e}')
</ARG>