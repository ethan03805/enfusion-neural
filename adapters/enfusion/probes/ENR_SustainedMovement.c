// Isolated benchmark only. Uses the ordinary controlled soldier and engine actions.
modded class ArmaReforgerScripted
{
 override void OnUpdate(BaseWorld world, float timeslice)
 {
  super.OnUpdate(world, timeslice);
  if (!world || !ENR_PlayableState.Controller) return;
  float pathTime = ENR_PlayableState.Elapsed - 30;
  if (pathTime < 0 || pathTime >= 210)
  {
   GetGame().GetInputManager().SetActionValue("CharacterForward", 0);
   return;
  }
  float phase = pathTime;
  while (phase >= 42) phase -= 42;
  float yaw = ENR_PlayableConfig.Yaw;
  float forward = 0;
  if (phase < 18) forward = 1;
  else if (phase < 21) yaw += 180 * (phase - 18) / 3;
  else if (phase < 39)
  {
   yaw += 180;
   forward = 1;
  }
  else yaw += 180 + 180 * (phase - 39) / 3;
  ENR_PlayableState.Controller.SetHeadingAngle(yaw * Math.DEG2RAD, true);
  GetGame().GetInputManager().SetActionValue("CharacterForward", forward);
 }
}
