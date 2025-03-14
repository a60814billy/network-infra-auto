# device preconfig 

## IOS-XE

ref: https://napalm.readthedocs.io/en/latest/support/ios.html

```
archive
 path bootflash:backup_cfg
 maximum 5
ip scp server enable
```

## NXOS

ref: https://napalm.readthedocs.io/en/latest/support/nxos.html

```
feature nxapi
feature scp-server
```

## IOS XR

ref: https://github.com/fooelisa/pyiosxr

```
xml agent tty iteration off
```