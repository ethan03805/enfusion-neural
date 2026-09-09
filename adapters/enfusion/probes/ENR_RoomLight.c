#ifdef WORKBENCH
class ENR_RoomLight
{
 static bool Attempted;
 static LightEntity LocalLight;

 static void Init()
 {
  if (Attempted) return;
  Attempted = true;
  Color lightColor = new Color(1, 1, 1, 1);
  LocalLight = LightEntity.CreateLight(LightType.POINT, LightFlags.CASTSHADOW, ENR_RoomLightConfig.Radius, lightColor, ENR_RoomLightConfig.LV, ENR_RoomLightConfig.Position);
  if (!LocalLight) { Print("ENR_ROOM_LIGHT failed=create"); return; }
  LocalLight.SetNearPlane(ENR_RoomLightConfig.Near);
  LocalLight.SetDistanceAtt(2);
  LocalLight.SetLensFlareIndex(-1);
  LocalLight.SetEnabled(ENR_RoomLightConfig.Enabled);
  PrintFormat("ENR_ROOM_LIGHT created case=%1 requested_lv=%2 requested_rgb=1,1,1 requested_attenuation=2 requested_flare=-1", ENR_RoomLightConfig.Case, ENR_RoomLightConfig.LV);
  PrintFormat("ENR_ROOM_LIGHT readback enabled=%1 shadow=%2 radius=%3 near=%4 position=%5", LocalLight.IsEnabled(), LocalLight.IsCastShadow(), LocalLight.GetRadius(), LocalLight.GetNearPlane(), LocalLight.GetOrigin());
  if (ENR_RoomLightConfig.UseClipControl)
  {
   LocalLight.SetIntensityEVClip(-10);
   Print("ENR_ROOM_LIGHT clip requested_ev=-10");
  }
 }
}
#endif
