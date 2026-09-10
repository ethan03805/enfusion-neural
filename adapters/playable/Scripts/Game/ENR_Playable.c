// Loaded only by the isolated local prototype project. No renderer hooks.
class ENR_PlayableState
{
 static float Elapsed;
 static float NextLog;
 static bool Attempted;
 static IEntity Player;
 static CharacterControllerComponent Controller;
}

modded class ArmaReforgerScripted
{
 override void OnUpdate(BaseWorld world, float timeslice)
 {
  super.OnUpdate(world, timeslice);
  if (!world) return;
  ENR_PlayableState.Elapsed += timeslice;
  ChimeraWorld chimera = GetGame().GetWorld();
  if (!chimera) return;
  TimeAndWeatherManagerEntity weather = chimera.GetTimeAndWeatherManager();
  if (!weather) return;
  if (!ENR_PlayableState.Attempted && ENR_PlayableState.Elapsed > 4)
  {
   PlayerController controller = GetGame().GetPlayerController();
   if (!controller) return;
   ENR_PlayableState.Attempted = true;
   weather.SetDate(1989, 6, 21, true);
   weather.SetTimeOfTheDay(ENR_PlayableConfig.Hour, true);
   weather.ForceWeatherTo(true, "Clear", 0, 86400);
   weather.SetWindSpeedOverride(true, 0);
   vector position = ENR_PlayableConfig.Position;
   position[1] = world.GetSurfaceY(position[0], position[2]) + 0.2;
   Resource resource = Resource.Load("{26A9756790131354}Prefabs/Characters/Factions/BLUFOR/US_Army/Character_US_Rifleman.et");
   if (!resource || !resource.IsValid()) { Print("ENR_LIVE spawn_resource_failed"); return; }
   EntitySpawnParams parameters = new EntitySpawnParams();
   parameters.TransformMode = ETransformMode.WORLD;
   Math3D.AnglesToMatrix(Vector(ENR_PlayableConfig.Yaw, 0, 0), parameters.Transform);
   parameters.Transform[3] = position;
   ENR_PlayableState.Player = GetGame().SpawnEntityPrefab(resource, world, parameters);
   if (!ENR_PlayableState.Player) { Print("ENR_LIVE spawn_failed"); return; }
   ENR_PlayableState.Controller = CharacterControllerComponent.Cast(ENR_PlayableState.Player.FindComponent(CharacterControllerComponent));
   ENR_Settings.Log();
   int nw, nh, rw, rh; System.GetNativeResolution(nw, nh); System.GetRenderingResolution(rw, rh);
   PrintFormat("ENR_LIVE dimensions native=%1x%2 rendering=%3x%4", nw, nh, rw, rh);
   bool controlled = controller.SetControlledEntity(ENR_PlayableState.Player);
   SCR_EditorManagerEntity.CloseInstance();
   controller.SetCharacterCameraRenderActive(true);
   PrintFormat("ENR_LIVE player_spawned=%1 controlled=%2 position=%3", ENR_PlayableState.Player != null, controlled, position);
  }
  if (ENR_PlayableConfig.Automatic && ENR_PlayableState.Controller)
  {
   float pathTime = ENR_PlayableState.Elapsed - 30;
   if (pathTime >= 0 && pathTime < 20)
    ENR_PlayableState.Controller.SetMovement(1, "0 0 1");
   else if (pathTime >= 20 && pathTime < 30)
   {
    ENR_PlayableState.Controller.SetMovement(0, "0 0 1");
    ENR_PlayableState.Controller.SetHeadingAngle((ENR_PlayableConfig.Yaw + 25 * Math.Sin((pathTime - 20) * 0.628319)) * Math.DEG2RAD, true);
   }
   else if (pathTime >= 30)
    ENR_PlayableState.Controller.SetMovement(0, "0 0 1");
  }
  if (ENR_PlayableState.Elapsed >= ENR_PlayableState.NextLog)
  {
   ENR_PlayableState.NextLog = ENR_PlayableState.Elapsed + 1;
   vector camera[4]; world.GetCurrentCamera(camera);
   PrintFormat("ENR_LIVE simulation_s=%1 frame=%2 dt_ms=%3 camera=%4 direction=%5", ENR_PlayableState.Elapsed, world.GetFrameNumber(), timeslice * 1000, camera[3], camera[2]);
  }
 }
}
